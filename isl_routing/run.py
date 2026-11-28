# 터미널 실행 헬퍼
#
# 실행 (isl_routing 폴더에서):  python run.py
#   1. 할 일:      시뮬레이션 (main_isl.py) / C 학습 (rl/train_rl.py) / C 적응 (rl/adapt_rl.py) / B, C 평가 (eval_routes.py) / 테스트
#   실험 순서: C 학습 (학습 전용 격자, 기본 10x10) -> (선택) C 적응 (평가할 격자에서 짧게) -> B, C 비교 평가 (다른 격자)
#   결과 지표는 측정 흐름(흐름 0) 기준. 다른 GSL 흐름(1~3)은 흐름별 결과(flow_analysis)에서만 봄
#   2. grid 구조:    6x6 격자 / 크기 지정 격자 / Iridium 크기(6x11) / Starlink 크기(72x22). 모두 직사각형 가상 격자
#                  (끝은 막힘, 원형 연결과 극지방 없음, 링크 지연 상하 7, 좌우 2 step 고정)
#   3. 혼잡 단계:  base / high / severe (학습, 평가 기본은 high, severe)
#   4. 라우팅:     B / A / C
#   설정은 config_isl.py, rl/config_rl.py 기본값: 주 흐름 4개, 핫스팟 지속 1초, State 15개 (coarse), 행동 마스크 link, 보상 7차, hard update
#   그 밖에 시드, 에피소드 수를 묻고, 마지막에 설정과 저장 위치를 보여 준 뒤 실행 여부를 확인함
#   실행이 끝나면 실제 결과 폴더 경로를 보여 줌
#   그래프 자동 저장: 시뮬레이션이 끝나면 흐름별 결과(flow_analysis_*.png), C 학습이 끝나면 학습 곡선(learning_curve_eval.png)
#   테스트별 학습 곡선 비교는 python viz/plot_compare_tests.py "이름=학습폴더" ... (설명은 그 파일 맨 위)
#   엔터만 누르면 [괄호] 안의 기본값을 씀

import glob
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser('~')
LEVELS = ['base', 'high', 'severe']
STEP = [0]   # 질문 번호 (화면에 [1], [2] ... 로 표시)


def step(title):
    STEP[0] += 1
    return f'\n[{STEP[0]}] {title}'


def ask_choice(title, options, default=1):
    # options: 번호 입력으로 고름
    print(step(title))
    for i, (label, _) in enumerate(options, 1):
        print(f'  {i}. {label}')
    while True:
        s = input(f'번호 입력 [{default}]: ').strip()
        if not s:
            return options[default - 1][1]
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1][1]
        print(f'  1~{len(options)} 사이 숫자 입력')


def ask_int(title, default, lo=1, hi=100000, help=None):
    # help: 질문 아래에 보여 줄 설명 줄들 (있으면 질문, 설명, 입력 칸 순서로 보여 줌)
    prompt = step(title)
    if help:
        print(prompt)
        for line in help:
            print(f'  {line}')
        prompt = '입력'
    while True:
        s = input(f'{prompt} [{default}]: ').strip()
        if not s:
            return default
        if s.isdigit() and lo <= int(s) <= hi:
            return int(s)
        print(f'  {lo}~{hi} 사이 숫자 입력')


def ask_ratio(title, default, help=None):
    # 'b:h:s' 형식 (예 1:1:2), 합이 0보다 커야 함
    prompt = step(title)
    if help:
        print(prompt)
        for line in help:
            print(f'  {line}')
        prompt = '입력'
    while True:
        s = input(f'{prompt} [{default}]: ').strip().replace(' ', '') or default
        parts = s.split(':')
        if len(parts) == 3 and all(p.replace('.', '', 1).isdigit() for p in parts) and sum(float(p) for p in parts) > 0:
            return s
        print('  base:high:severe 형식으로 입력 (예: 0:1:2, 1:1:2)')


def ask_size(title, default):
    prompt = step(title)
    while True:
        s = input(f'{prompt} (예: 8x8) [{default}]: ').strip().lower().replace(' ', '') or default
        a, _, b = s.partition('x')
        if a.isdigit() and b.isdigit() and 2 <= int(a) <= 100 and 2 <= int(b) <= 100:
            return f'{int(a)}x{int(b)}'
        print('  가로x세로 형식, 각각 2~100 사이 입력')


def ask_topology(default=1, size='8x8', title='grid 구조 선택'):
    kind = ask_choice(title, [
        ('6 x 6 가상 격자 (기본)', 'grid'),
        ('원하는 가상 grid (예: 8x8)', 'grid-size'),
        ('Iridium 크기 직사각형 격자 (6 x 11)', 'grid:6x11'),
        ('Starlink 크기 직사각형 격자 (72 x 22, 위성 1,584개)', 'grid:72x22'),
    ], default)

    if kind == 'grid-size':
        return 'grid:' + ask_size('격자 크기 입력 (궤도면 수 x 궤도면당 위성 수)', size)
    return kind


def state_mode_of(modelPath):
    # 학습 폴더의 run_info.txt에 적힌 State 방식 (없으면 이전 방식 'full')
    try:
        text = open(os.path.join(os.path.dirname(modelPath), 'run_info.txt'), encoding='utf-8').read()
    except OSError:
        return 'full'
    m = re.search(r'stateMode=(\w+)', text)
    return m.group(1) if m else 'full'


def model_label(f, root):
    from rl.model_info import model_grid
    return f'{os.path.relpath(os.path.dirname(f), root)} / {os.path.basename(f)}  [학습 격자: {model_grid(f)}]'


def find_models(topology=None):
    # 홈 폴더 rl_models (하위 폴더 포함)의 C 모델을 최신순으로 찾음. 학습 격자와 상관없이 모두 보여 줌
    #   (다른 격자로 학습한 모델을 이 격자에서 평가하는 실험 가능. 학습 격자는 목록에 [학습 격자: ...]로 표시)
    # 지금 설정(config_rl.py의 RL.stateMode)으로 학습한 모델만. 이전 State로 학습한 모델은 config_rl.py를 바꿔야 쓸 수 있음
    from config_isl import config_isl
    from rl.config_rl import config_rl
    RL = config_rl(config_isl())
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(HOME, 'rl_models'))
    found = glob.glob(os.path.join(root, '**', 'routeC_*', 'model_*.pt'), recursive=True)
    found = sorted([f for f in found if state_mode_of(f) == RL.stateMode], key=os.path.getmtime, reverse=True)
    if not found:
        print(f'\n지금 State({RL.obsDim}개, {RL.stateMode})로 학습한 C 모델 없음. 먼저 "C 학습" 실행 필요')
    return root, found


def pick_model(topology=None, title='사용할 C 모델 선택 (최신순)'):
    # 모델 1개 고르기 (시뮬레이션용)
    root, found = find_models()
    if not found:
        return None
    options = [(model_label(f, root), f) for f in found[:9]]
    return ask_choice(title, options)


def pick_models(topology=None, title='사용할 C 모델 선택 (최신순)'):
    # 평가, 적응용: 같은 때 학습한 학습 시드 모델(_s0, _s1 ...)의 model_final.pt를 한 번에 고르는 선택지를 맨 위에 보여 줌
    # 돌려주는 값은 쉼표로 이은 모델 경로 (eval_routes.py는 모델마다 따로 평가, 적응은 모델마다 따로 적응)
    from rl.model_info import model_grid
    root, found = find_models()
    if not found:
        return None
    groups = {}
    for f in found:
        if os.path.basename(f) != 'model_final.pt':
            continue
        name = os.path.basename(os.path.dirname(f))
        m = re.match(r'(.*)_s(\d+)(_\d+)?$', name)   # routeC_grid10x10_2026-11-24_s0 (같은 날 또 학습하면 _s0_2)
        if m:
            groups.setdefault(m.group(1) + (m.group(3) or ''), []).append((int(m.group(2)), f))
    options = []
    for key, items in groups.items():
        if len(items) > 1:
            items.sort()
            seeds = ', '.join(f's{sd}' for sd, _ in items)
            options.append((f'{key} 학습 시드 {len(items)}개 모두 ({seeds}) / model_final.pt  [학습 격자: {model_grid(items[0][1])}]  <- 보고서용',
                            ','.join(f for _, f in items)))
    options = options[:3] + [(model_label(f, root), f) for f in found[:9 - min(len(options), 3)]]
    return ask_choice(title, options)


def save_info(task, summary, topoTag):
    # 할 일별 저장 위치 안내: (보여 줄 위치, 설명 줄들, 실제 폴더를 찾을 패턴)
    d = dict(summary)
    today = time.strftime('%Y-%m-%d')
    t = f'_{topoTag}' if topoTag else ''
    if task == 'sim':
        name = ('routeB' if d.get('라우팅') == 'config 기본 (B)' else d.get('라우팅')) + f"_{d.get('혼잡 단계')}{t}"
        folder = os.path.join(HOME, 'isl_saved_runs', f'{name}_{today}')
        return (folder,
                ['결과 CSV, 그래프(PNG, 흐름별 결과 flow_analysis 포함), 애니메이션(GIF), 실행 조건(run_info.txt), 실행한 코드 복사본',
                 f'방금 결과는 {os.path.join(HERE, "results")} 에도 있음 (다음 실행 때 지워짐)',
                 '같은 날 다른 시드면 이름 뒤에 _2, _3 붙음 (같은 시드면 덮어씀)'],
                folder + '*')
    if task == 'train':
        folder = os.path.join(HOME, 'rl_models', f'routeC{t}_{today}')
        return (folder,
                ['폴더 이름 끝에 학습 시드가 붙음 (예: _s0)',
                 'model_final.pt (최종 모델), model_ep10.pt 등 (10 에피소드마다)',
                 'train_log.csv (학습 중 기록), eval_log.csv (5 에피소드마다 검증 평가, ε 0), run_info.txt (학습 조건)',
                 '끝나면 학습 곡선(learning_curve_eval.png)과 판정표(learning_targets.md)를 첫 학습 시드 폴더에 자동 저장',
                 '같은 날 또 학습하면 이름 뒤에 _2, _3 붙음'],
                folder + '*')
    if task == 'adapt':
        folder = os.path.join(HOME, 'rl_models', 'routeC_adapt_')
        return (folder + '<원래 모델 폴더>_to_' + (topoTag or 'grid') + f'_{today}',
                ['모델마다 폴더 하나: model_final.pt (적응한 모델), train_log.csv, eval_log.csv (적응 전, 뒤 검증), run_info.txt',
                 '적응한 모델은 시뮬레이션, 평가에서 모델 목록에 routeC_adapt_... 로 보임'],
                folder + '*')
    if task == 'eval':
        folder = os.path.join(HOME, 'isl_saved_runs', f'eval{t}_{today}')
        return (folder,
                ['summary.csv (라우팅별, 혼잡 단계별 결과 표, 측정 흐름 기준), per_seed.csv (평가 시드별), run_info.txt (평가 조건, C 모델 학습 격자)',
                 '막대 비교 그래프가 필요하면: python viz/plot_eval.py 평가폴더',
                 '같은 날 또 평가하면 이름 뒤에 _2, _3 붙음'],
                folder + '*')
    return None


def newest(pattern, since):
    # 실행 중에 새로 생기거나 바뀐 폴더 중 가장 최근 것
    dirs = [p for p in glob.glob(pattern) if os.path.isdir(p) and os.path.getmtime(p) >= since - 1]
    return max(dirs, key=os.path.getmtime) if dirs else None


def main():
    print('=' * 60)
    print(' ISL 라우팅 시뮬레이션 실행 Helper')
    print(' 번호 입력 후 엔터. 엔터만 누르면 괄호 안 기본값 사용')
    print('=' * 60)

    task = ask_choice('할 일 선택', [
        ('시뮬레이션 실행 (결과 CSV, 그래프, 애니메이션 저장)', 'sim'),
        ('강화학습 C 학습 및 모델 저장 (학습 전용 격자, 기본 10x10)', 'train'),
        ('C 적응 (학습한 모델을 평가할 격자에서 짧게 추가 학습)', 'adapt'),
        ('같은 조건으로 B, C 비교 평가', 'eval'),
        ('테스트 (코드 동작 확인, 약 10초)', 'test'),
    ])
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    summary = []
    topology = 'grid'

    if task == 'test':
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
    else:
        if task == 'train':   # 학습은 학습 전용 격자 (기본 10x10), 평가는 다른 격자에서
            topology = ask_topology(2, '10x10', '학습 격자 선택 (기본: 원하는 가상 grid 10x10, 학습 전용)')
        elif task == 'adapt':
            topology = ask_topology(2, '24x24', '적응할 격자 선택 (나중에 평가할 격자)')
        else:
            topology = ask_topology(title='실행할 격자 선택 (C 모델은 다른 격자로 학습한 것도 고를 수 있음)')
        env['ISL_TOPOLOGY'] = topology
        summary.append(('grid 구조', topology))

        if task == 'sim':
            level = ask_choice('혼잡 단계 선택', [('base (평상시)', 'base'), ('high (붐빔)', 'high'), ('severe (매우 붐빔)', 'severe')])
            route = ask_choice('라우팅 방식 선택', [
                ('B DRA (config 기본)', None), ('A 최단 경로 (Dijkstra)', 'routeA'), ('C 강화학습 (학습된 모델 필요)', 'routeC')])
            seed = ask_int('시작 시드 입력 (같은 시드 = 같은 혼잡 상황, 평가 시드 1~20)', 1)
            cmd = [sys.executable, 'main_isl.py', str(seed), level]
            summary += [('혼잡 단계', level), ('라우팅', route or 'config 기본 (B)'), ('시작 시드', seed)]
            if route:
                cmd.append(route)
            if route == 'routeC':
                model = pick_model(topology)
                if not model:
                    return
                cmd.append(model)
                summary.append(('C 모델', model))

        elif task == 'train':
            episodes = ask_int('학습 에피소드 수', 80, help=[
                '에피소드 1개 = 10초짜리 시뮬레이션 1번. 이 수만큼 매번 다른 혼잡 상황을 겪으며 배움',
                '기본 80: 7차 테스트와 같음. 성능이 에피소드 약 25~40에 오르기 시작해 50 전후에 안정됨',
                '시간: 에피소드 1개에 약 40~80초 (검증 포함)'])
            trainSeed = ask_int('학습 시드', 0, 0, 4, help=[
                '신경망의 처음 값을 정하는 번호. 같은 설정이라도 번호가 다르면 결과가 조금씩 달라짐',
                '학습 시드가 늘어나면 더 정확한 성능 측정 가능',
                '0: 동일 조건에서 1개 돌아감, 1: 동일 조건에서 2개 돌아감, 2: 동일 조건에서 3개 돌아감 (동시에 실행)'])
            ratio = ask_ratio('혼잡 단계 비율 base:high:severe', '0:1:2', help=[
                'base 평상시, high 붐빔, severe 매우 붐빔을 어떤 비율로 섞어 학습할지. 0이면 그 단계는 학습, 검증에서 뺌',
                '기본 0:1:2: base 없이 high 1번에 severe 2번 꼴 (7차와 같음, 시간 때문에 base는 뺌)',
                '예: 1:1:2 (base 포함), 1:1:1 (똑같이), 0:0:1 (severe만)'])
            seeds = list(range(trainSeed + 1))   # 0 -> [0], 1 -> [0, 1], 2 -> [0, 1, 2]
            cmd = [sys.executable, os.path.join('rl', 'train_rl.py'), str(episodes), '0', '0', ratio]
            cmds = [cmd[:4] + [str(sd), ratio] for sd in seeds]
            summary += [('학습 에피소드', f'{episodes}개 (검증 평가 포함 예상 시간 약 {max(1, episodes * 2 // 3)}~{max(1, episodes * 4 // 3)}분, 동시에 돌리면 조금 더 걸림)'),
                        ('학습 시드', f'{", ".join(map(str, seeds))} ({len(seeds)}개 동시 실행)'), ('단계 비율', f'base : high : severe = {ratio.replace(":", " : ")}')]

        elif task == 'adapt':
            models = pick_models(title='적응할 C 모델 선택 (다른 격자로 학습한 모델)')
            if not models:
                return
            episodes = ask_int('적응 에피소드 수', 5, 1, 80, help=[
                '평가할 격자에서 이만큼만 추가로 학습 (적응 전용 시드 2001~, 평가 시드 1~20과 겹치지 않음)',
                'ε 0.05 고정, 학습률은 학습 때의 1/10. 적응 전, 뒤에 검증 평가 (측정 흐름 기준)'])
            cmds = [[sys.executable, os.path.join('rl', 'adapt_rl.py'), m, str(episodes)] for m in models.split(',')]
            cmd = cmds[0]
            summary += [('C 모델', models), ('적응 에피소드', f'{episodes}개 (모델 {len(cmds)}개 동시 실행)')]

        else:   # eval
            level = ask_choice('혼잡 단계 선택', [('high, severe (기본, 학습과 같음)', 'high,severe'), ('전부 (base, high, severe)', 'all')]
                               + [(lv, lv) for lv in LEVELS])
            routes = ask_choice('비교할 라우팅 선택', [
                ('B, C (기본)', 'routeB,routeC'), ('A, B, C 모두', 'routeA,routeB,routeC'), ('B만 (모델 없이)', 'routeB'), ('C만', 'routeC')])
            model = 'none'
            if 'routeC' in routes:
                model = pick_models(topology)
                if not model:
                    return
            episodes = ask_int('평가 에피소드 수 입력 (평가 시드 1부터)', 10, 1, 20)
            cmd = [sys.executable, 'eval_routes.py', model, level, routes, str(episodes)]
            summary += [('혼잡 단계', level), ('라우팅', routes), ('C 모델', model), ('평가 에피소드', episodes)]

    if task != 'test':   # 지금 기본 설정 (7차 기준)을 확인 화면에 함께 보여 줌
        sys.path.insert(0, HERE)
        os.environ['ISL_TOPOLOGY'] = topology
        from config_isl import config_isl
        from rl.config_rl import config_rl
        P = config_isl()
        RL = config_rl(P)
        summary.append(('환경', f'주 흐름 {P.numFlows}개 (흐름마다 초당 {P.genRate}개), 핫스팟 지속 {P.evDurationMean / 1000:.1f}초, 기한 {P.deadline} ms'))
        if task == 'train':
            perFlow = RL.trainEvery // max(P.numFlows, 1)
            summary.append(('학습 설정', f'State: {RL.obsDim}개, '
                                       f'결정 {RL.trainEvery}번마다 학습(흐름 {P.numFlows}개라 흐름 하나당 {perFlow}번꼴, 에피소드당 학습 횟수를 흐름 1개일 때와 같게 맞춤), '
                                       f'타깃 복사 학습 {RL.targetUpdate}마다(정답 계산용 신경망을 에피소드 약 1번마다 새로 맞춤, 너무 자주 하면 학습이 지나치게 빨리 시작됨), '
                                       f'ε: {RL.epsDecaySteps:,}번(처음엔 전부 무작위로 움직이다가 이만큼의 결정 동안 무작위 비율을 5%까지 줄임, 에피소드 약 10), '
                                       f'γ {RL.gamma:.3f}(측정 흐름 {P.maxFlowHops}홉, 망 크기에 비례)'))

    topoTag = '' if topology == 'grid' else topology.replace(':', '')
    save = save_info(task, summary, topoTag)

    print('\n' + '-' * 60)
    print(' 실행 설정 확인')
    for k, v in summary:
        print(f'   {k:10s} {v}')
    for c in (cmds if task in ('train', 'adapt') else [cmd]):
        print(f'   명령       python {" ".join(c[1:])}')
    if save:
        print(f'   저장 위치  {save[0]}')
        for line in save[1]:
            print(f'              {line}')
    print('-' * 60)
    if input('실행 (Y/n): ').strip().lower() in ('n', 'no', '아니오'):
        print('취소함')
        return

    t0 = time.time()
    if task in ('train', 'adapt') and len(cmds) > 1:   # 학습 시드(모델) 여러 개를 동시에 실행, 각자 기록 파일에 출력
        logDir = os.path.join(HERE, 'results')
        os.makedirs(logDir, exist_ok=True)
        procs = []
        for i, c in enumerate(cmds):
            log = os.path.join(logDir, f'train_s{c[4]}.log' if task == 'train' else f'adapt_{i}.log')
            procs.append(subprocess.Popen(c, cwd=HERE, env=env, stdout=open(log, 'w', encoding='utf-8'), stderr=subprocess.STDOUT))
            print(f' {"학습 시드 " + c[4] if task == "train" else "적응 " + str(i)} 시작, 진행 기록: {log}')
        print(' 모두 끝날 때까지 기다림 (진행 상황은 위 기록 파일을 열어 보면 됨)')
        code = max(p.wait() for p in procs)
    else:
        code = subprocess.call(cmd, cwd=HERE, env=env)
    print('\n' + '=' * 60)
    print(f' {"완료" if code == 0 else "오류로 멈춤 (위 메시지 확인)"}  ({(time.time() - t0) / 60:.1f}분)')
    if save and code == 0:
        if task == 'train':   # 학습 시드마다 폴더가 하나씩 생김
            made = sorted(p_ for p_ in glob.glob(save[2]) if os.path.isdir(p_) and os.path.getmtime(p_) >= t0 - 1)
            for p_ in made or [save[0]]:
                print(f' 결과 폴더  {p_}')
            made = [p_ for p_ in made if os.path.exists(os.path.join(p_, 'eval_log.csv'))]
            if made:   # 학습 곡선 그래프와 판정표 자동 저장 (학습 시드가 여러 개면 한 그림에 겹쳐 그림)
                print(' 학습 곡선 그리는 중...')
                c2 = subprocess.call([sys.executable, os.path.join('analysis', 'learning_targets.py')] + made,
                                     cwd=HERE, env=env, stdout=subprocess.DEVNULL)
                print(f' 학습 곡선  {os.path.join(made[0], "learning_curve_eval.png")}' if c2 == 0 else
                      f' 학습 곡선 그리기 실패, 직접 실행: python analysis/learning_targets.py {" ".join(made)}')
        elif task == 'adapt':
            for p_ in sorted(p_ for p_ in glob.glob(save[2]) if os.path.isdir(p_) and os.path.getmtime(p_) >= t0 - 1):
                print(f' 결과 폴더  {p_}')
        else:
            print(f' 결과 폴더  {newest(save[2], t0) or save[0]}')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\n멈춤')
