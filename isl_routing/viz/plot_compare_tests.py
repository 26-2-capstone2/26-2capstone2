# 테스트(학습 설정)별 학습 곡선 비교 - 여러 번의 학습을 한 그림에 겹쳐 그림 (1차, 2차 ... 테스트 비교용)
#
# 실행 (isl_routing 폴더에서):
#   python viz/plot_compare_tests.py "이름=학습폴더" "이름=학습폴더" ... [-o 저장경로.png]
#   폴더 자리에 * 를 쓰면 학습 시드 폴더 여러 개를 한 테스트로 묶어 평균을 그림 (따옴표로 감쌀 것)
#   예) python viz/plot_compare_tests.py "7차 이리듐=~/rl_models/routeC_iridium_2026-11-08_s*" \
#                                        "8차 이리듐=~/rl_models/routeC_iridium_2026-11-10_s*"
#   이름 없이 폴더만 주면 폴더 이름을 그대로 씀
#
# 입력: 학습폴더마다 train_rl.py가 만든 eval_log.csv (검증 평가, ε 0, 전체 흐름 합계)
# 그림: 열 = 혼잡 단계, 행 = 기한 내 도착률 / 1분당 연속 손실 / 최대 연속 손실, 가로축 = 학습 에피소드
#       선 = 학습 시드 평균, 옅은 띠 = 학습 시드 중 최소~최대
# 저장: -o 로 준 경로, 없으면 isl_routing/results/compare_tests.png
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)   # isl_routing를 import 경로에 추가

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from viz.viz_colors import use_korean_font, viz_colors

ROWS = [('onTimeRate', '기한 내 도착률 (%)'), ('burstPerMin', '1분당 연속 손실 (회)'), ('maxConsecLoss', '최대 연속 손실 (개)')]
LEVEL_ORDER = ['base', 'high', 'severe']
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#8e5bd6', '#d62728', '#8c564b', '#e377c2', '#7f7f7f', '#17becf']


def read_eval(trainDir):
    with open(os.path.join(trainDir, 'eval_log.csv'), encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def parse_args(argv):
    out, tests = None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '-o' and i + 1 < len(argv):
            out = os.path.expanduser(argv[i + 1])
            i += 2
            continue
        name, sep, pattern = a.partition('=')
        if not sep:
            name, pattern = os.path.basename(os.path.normpath(a)), a
        dirs = sorted(d for d in glob.glob(os.path.expanduser(pattern)) if os.path.exists(os.path.join(d, 'eval_log.csv')))
        if dirs:
            tests.append((name, dirs))
        else:
            print(f'eval_log.csv가 있는 폴더 없음, 건너뜀: {pattern}')
        i += 1
    return tests, out or os.path.join(HERE, 'results', 'compare_tests.png')


def curves(dirs, level, col):
    # 학습 시드 폴더별 (에피소드 -> 값)을 모아, 모든 폴더에 있는 에피소드만 평균/최소/최대
    per = []
    for d in dirs:
        rows = [r for r in read_eval(d) if r['level'] == level and r.get(col, '') != '']
        per.append({int(r['episode']): float(r[col]) for r in rows})
    eps = sorted(set.intersection(*(set(p) for p in per))) if per else []
    v = np.array([[p[e] for e in eps] for p in per])
    return np.array(eps), v


def main():
    tests, out = parse_args(sys.argv[1:])
    if not tests:
        print(__doc__ if __doc__ else '사용법: python viz/plot_compare_tests.py "이름=학습폴더" ...')
        print('사용법: python viz/plot_compare_tests.py "이름=학습폴더(* 가능)" ... [-o 저장경로.png]')
        return
    levels = sorted({r['level'] for _, dirs in tests for d in dirs for r in read_eval(d)},
                    key=lambda x: LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 99)
    C = viz_colors()
    use_korean_font(C)
    fig, axes = plt.subplots(len(ROWS), len(levels), figsize=(7 * len(levels), 4 * len(ROWS)), sharex=True, squeeze=False)
    fig.patch.set_facecolor('white')
    for j, lv in enumerate(levels):
        for i, (col, ylabel) in enumerate(ROWS):
            ax = axes[i][j]
            for k, (name, dirs) in enumerate(tests):
                eps, v = curves(dirs, lv, col)
                if not len(eps):
                    continue
                color = COLORS[k % len(COLORS)]
                label = f'{name} (학습 시드 {len(dirs)}개)' if len(dirs) > 1 else name
                ax.plot(eps, v.mean(axis=0), color=color, lw=2, marker='o', ms=3, label=label if i == 0 and j == 0 else None)
                if len(dirs) > 1:
                    ax.fill_between(eps, v.min(axis=0), v.max(axis=0), color=color, alpha=0.15, lw=0)
            if i == 0:
                ax.set_title(f'{lv} (검증, ε 0)')
                ax.set_ylim(0, 102)
            if j == 0:
                ax.set_ylabel(ylabel)
            if i == len(ROWS) - 1:
                ax.set_xlabel('학습 에피소드 (10초 단위)')
            ax.grid(color=C.grid, lw=0.8)
            for s in ('top', 'right'):
                ax.spines[s].set_visible(False)
    axes[0][0].legend(frameon=True, fontsize=9, loc='lower right')
    fig.suptitle('테스트별 학습 곡선 비교 (선: 학습 시드 평균, 띠: 학습 시드 최소~최대, 전체 흐름 합계)', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f'저장: {out}')


if __name__ == '__main__':
    main()
