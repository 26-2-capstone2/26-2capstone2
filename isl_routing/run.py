# 터미널 실행 헬퍼
#
# 실행 (isl_routing 폴더에서):  python run.py
#   1. 할 일:      시뮬레이션 (main_isl.py) / C 학습 (rl/train_rl.py) / B, C 평가 (eval_routes.py) / 테스트
#   2. grid 구조:    6x6 격자 / 크기 지정 격자 / Iridium / Starlink / Starlink 축소판
#   3. 혼잡 단계:  base / high / severe (학습, 평가 기본은 high, severe)
#   4. 라우팅:     B / A / C
#   설정은 7차 테스트 기준 (config_isl.py, rl/config_rl.py 기본값): 주 흐름 4개, 핫스팟 지속 1초, State 15개, hard update
#   그 밖에 시드, 에피소드 수를 묻고, 마지막에 설정과 저장 위치를 보여 준 뒤 실행 여부를 확인함
#   실행이 끝나면 실제 결과 폴더 경로를 보여 줌
#   엔터만 누르면 [괄호] 안의 기본값을 씀

import glob
import os
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
    # options: 번호 입력으로 고름.
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


def ask_topology():
    kind = ask_choice('grid 구조 선택', [
        ('6 x 6 가상 격자 (기본)', 'grid'),
        ('원하는 가상 grid (예: 8x8)', 'grid-size'),
        ('Iridium (6 x 11 극궤도)', 'iridium'),
        ('Starlink 1차 셸 (72 x 22, 위성 1,584개)', 'starlink'),
        ('Starlink 축소판 (크기 지정, 예: 12x12)', 'starlink-size'),
    ])

    if kind == 'grid-size':
        return 'grid:' + ask_size('격자 크기 입력 (궤도면 수 x 궤도면당 위성 수)', '8x8')
    if kind == 'starlink-size':
        return 'starlink:' + ask_size('Starlink 축소판 크기 입력', '12x12')
    return kind


def state_mode_of(modelPath):
    # 학습 폴더의 run_info.txt에 적힌 State 방식 (없으면 이전 방식 'full')
    try:
        text = open(os.path.join(os.path.dirname(modelPath), 'run_info.txt'), encoding='utf-8').read()
    except OSError:
        return 'full'
    return 'coarse' if 'stateMode=coarse' in text else 'noTrend' if 'stateMode=noTrend' in text else 'full'


def pick_model(topology):
    # 홈 폴더 rl_models (하위 폴더 포함)에서 이 grid 구조로 학습한 모델을 최신순으로 보여 줌
    # 지금 설정(State 15개, coarse)으로 학습한 모델만 보여 줌. 이전 State로 학습한 모델은 config_rl.py를 바꿔야 쓸 수 있음
    tag = '' if topology == 'grid' else topology.replace(':', '') + '_'
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(HOME, 'rl_models'))
    found = glob.glob(os.path.join(root, '**', f'routeC_{tag}20*', 'model_*.pt'), recursive=True)
    found = sorted([f for f in found if state_mode_of(f) == 'coarse'], key=os.path.getmtime, reverse=True)
    if not found:
        print(f'\n이 grid 구조({topology})와 지금 State(15개)로 학습한 C 모델 없음. 먼저 "C 학습" 실행 필요')
        return None
    options = [(f'{os.path.relpath(os.path.dirname(f), root)} / {os.path.basename(f)}', f) for f in found[:9]]
    return ask_choice('사용할 C 모델 선택 (최신순)', options)


def save_info(task, summary, topoTag):
    # 할 일별 저장 위치 안내: (보여 줄 위치, 설명 줄들, 실제 폴더를 찾을 패턴)
    d = dict(summary)
    today = time.strftime('%Y-%m-%d')
    t = f'_{topoTag}' if topoTag else ''
    if task == 'sim':
        name = ('routeB' if d.get('라우팅') == 'config 기본 (B)' else d.get('라우팅')) + f"_{d.get('혼잡 단계')}{t}"
        folder = os.path.join(HOME, 'isl_saved_runs', f'{name}_{today}')
        return (folder,
                ['결과 CSV, 그래프(PNG), 애니메이션(GIF), 실행 조건(run_info.txt), 실행한 코드 복사본',
                 f'방금 결과는 {os.path.join(HERE, "results")} 에도 있음 (다음 실행 때 지워짐)',
                 '같은 날 다른 시드면 이름 뒤에 _2, _3 붙음 (같은 시드면 덮어씀)'],
                folder + '*')
    if task == 'train':
        folder = os.path.join(HOME, 'rl_models', f'routeC{t}_{today}')
        return (folder,
                ['폴더 이름 끝에 학습 시드가 붙음 (예: _s0)',
                 'model_final.pt (최종 모델), model_ep10.pt 등 (10 에피소드마다)',
                 'train_log.csv (학습 중 기록), eval_log.csv (5 에피소드마다 검증 평가, ε 0), run_info.txt (학습 조건)',
                 '학습 곡선 목표 판정: python analysis/learning_targets.py 학습폴더',
                 '같은 날 또 학습하면 이름 뒤에 _2, _3 붙음'],
                folder + '*')
    if task == 'eval':
        folder = os.path.join(HOME, 'isl_saved_runs', f'eval{t}_{today}')
        return (folder,
                ['summary.csv (라우팅별, 혼잡 단계별 결과 표), run_info.txt (평가 조건)',
                 '그래프: python viz/plot_rl.py 학습폴더 summary.csv경로',
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
        ('강화학습 C 학습 및 모델 저장', 'train'),
        ('같은 조건으로 B, C 비교 평가', 'eval'),
        ('테스트 (코드 동작 확인, 약 10초)', 'test'),
    ])
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    summary = []
    topology = 'grid'

    if task == 'test':
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
    else:
        topology = ask_topology()
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

        else:   # eval
            level = ask_choice('혼잡 단계 선택', [('high, severe (기본, 학습과 같음)', 'high,severe'), ('전부 (base, high, severe)', 'all')]
                               + [(lv, lv) for lv in LEVELS])
            routes = ask_choice('비교할 라우팅 선택', [
                ('B, C (기본)', 'routeB,routeC'), ('A, B, C 모두', 'routeA,routeB,routeC'), ('B만 (모델 없이)', 'routeB'), ('C만', 'routeC')])
            model = 'none'
            if 'routeC' in routes:
                model = pick_model(topology)
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
                                       f'ε: {RL.epsDecaySteps:,}번(처음엔 전부 무작위로 움직이다가 이만큼의 결정 동안 무작위 비율을 5%까지 줄임, 에피소드 약 13)'))

    topoTag = '' if topology == 'grid' else topology.replace(':', '')
    save = save_info(task, summary, topoTag)

    print('\n' + '-' * 60)
    print(' 실행 설정 확인')
    for k, v in summary:
        print(f'   {k:10s} {v}')
    for c in (cmds if task == 'train' else [cmd]):
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
    if task == 'train' and len(cmds) > 1:   # 학습 시드 여러 개를 동시에 실행, 각자 기록 파일에 출력
        logDir = os.path.join(HERE, 'results')
        os.makedirs(logDir, exist_ok=True)
        procs = []
        for c in cmds:
            log = os.path.join(logDir, f'train_s{c[4]}.log')
            procs.append(subprocess.Popen(c, cwd=HERE, env=env, stdout=open(log, 'w', encoding='utf-8'), stderr=subprocess.STDOUT))
            print(f' 학습 시드 {c[4]} 시작, 진행 기록: {log}')
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
        else:
            print(f' 결과 폴더  {newest(save[2], t0) or save[0]}')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\n멈춤')
