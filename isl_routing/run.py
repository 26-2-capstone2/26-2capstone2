# 실행  터미널 실행 헬퍼..
#
# 실행 (isl_routing 폴더에서):  python run.py
#   1. 할 일:      시뮬레이션 (main_isl.py) / C 학습 (rl/train_rl.py) / A, B, C 평가 (eval_routes.py) / 테스트
#   2. grid 구조:    6x6 격자 / 크기 지정 격자 / Iridium / Starlink / Starlink 축소판
#   3. 혼잡 단계:  base / high / severe
#   4. 라우팅:     A, B 비교 / A / B / C
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


def ask_int(title, default, lo=1, hi=100000):
    prompt = step(title)
    while True:
        s = input(f'{prompt} [{default}]: ').strip()
        if not s:
            return default
        if s.isdigit() and lo <= int(s) <= hi:
            return int(s)
        print(f'  {lo}~{hi} 사이 숫자 입력')


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


def pick_model(topology):
    # 홈 폴더 rl_models에서 이 grid 구조로 학습한 모델을 최신순으로 보여 줌
    tag = '' if topology == 'grid' else topology.replace(':', '') + '_'
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(HOME, 'rl_models'))
    found = sorted(glob.glob(os.path.join(root, f'routeC_{tag}20*', 'model_*.pt')), key=os.path.getmtime, reverse=True)
    if not found:
        print(f'\n  이 grid 구조({topology})로 학습한 C 모델 없음. 먼저 "C 학습" 실행 필요')
        return None
    options = [(f'{os.path.basename(os.path.dirname(f))} / {os.path.basename(f)}', f) for f in found[:9]]
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
                 'train_log.csv (학습 중 기록), eval_log.csv (10 에피소드마다 검증 평가, ε 0), run_info.txt (학습 조건)',
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
        ('같은 조건으로 A, B, C 비교 평가', 'eval'),
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
            episodes = ask_int('학습 에피소드 수 입력 (10초씩, 혼잡 3단계 번갈아 학습)', 270)
            trainSeed = ask_int('학습 시드 입력 (신경망 초기값, 여러 개 돌릴 때 0, 1, 2)', 0, 0, 1000)
            cmd = [sys.executable, os.path.join('rl', 'train_rl.py'), str(episodes), '0', str(trainSeed)]
            summary += [('학습 에피소드', f'{episodes}개 (검증 평가 포함 예상 시간 약 {max(1, episodes // 3)}~{max(1, episodes // 2)}분)'),
                        ('학습 시드', trainSeed)]

        else:   # eval
            level = ask_choice('혼잡 단계 선택', [('전부 (base, high, severe)', 'all')] + [(lv, lv) for lv in LEVELS])
            routes = ask_choice('비교할 라우팅 선택', [
                ('B, C (기본)', 'routeB,routeC'), ('A, B, C 모두', 'routeA,routeB,routeC'), ('B만 (모델 없이)', 'routeB'), ('C만', 'routeC')])
            model = 'none'
            if 'routeC' in routes:
                model = pick_model(topology)
                if not model:
                    return
            episodes = ask_int('평가 에피소드 수 입력 (평가 시드 1부터)', 20, 1, 20)
            cmd = [sys.executable, 'eval_routes.py', model, level, routes, str(episodes)]
            summary += [('혼잡 단계', level), ('라우팅', routes), ('C 모델', model), ('평가 에피소드', episodes)]

    topoTag = '' if topology == 'grid' else topology.replace(':', '')
    save = save_info(task, summary, topoTag)

    print('\n' + '-' * 60)
    print(' 실행 설정 확인')
    for k, v in summary:
        print(f'   {k:10s} {v}')
    print(f'   명령       python {" ".join(cmd[1:])}')
    if save:
        print(f'   저장 위치  {save[0]}')
        for line in save[1]:
            print(f'              {line}')
    print('-' * 60)
    if input('실행 (Y/n): ').strip().lower() in ('n', 'no', '아니오'):
        print('취소함')
        return

    t0 = time.time()
    code = subprocess.call(cmd, cwd=HERE, env=env)
    print('\n' + '=' * 60)
    print(f' {"완료" if code == 0 else "오류로 멈춤 (위 메시지 확인)"}  ({(time.time() - t0) / 60:.1f}분)')
    if save and code == 0:
        print(f' 결과 폴더  {newest(save[2], t0) or save[0]}')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\n멈춤')
