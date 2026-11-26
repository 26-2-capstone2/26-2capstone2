# 최종 평가 그림 - eval_routes.py 결과(per_seed.csv)로 라우팅별 막대 비교 (B vs C, A를 골랐으면 A도)
#
# 실행 (isl_routing 폴더에서):
#   python viz/plot_eval.py 평가폴더
#   예) python viz/plot_eval.py ~/isl_saved_runs/eval_iridium_2026-11-10
#   자동으로 실행되지 않음. 필요할 때 직접 실행
#
# 막대 위 숫자 = 평가 시드(에피소드)별 값의 평균, 검은 선 = 평가 시드 간 표준편차
# C 모델이 여러 개(학습 시드별)면 평가 시드마다 모델들의 값을 먼저 평균 낸 뒤 같은 방식으로 계산
# 저장: 평가폴더/eval_compare.png
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing를 import 경로에 추가

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from viz.viz_colors import use_korean_font, viz_colors

PANELS = [   # (per_seed.csv 열, 제목) - 지표는 측정 흐름 기준
    ('onTimeRate', '측정 흐름 기한 내 도착률 (%)'),
    ('maxConsecLoss', '측정 흐름 최대 연속 손실 (개)'),
    ('burstPerMin', '측정 흐름 1분당 연속 손실 (회)'),
    ('burstLenP95', '측정 흐름 연속 손실 길이 95번째 백분위 (개)'),
    ('avgLatency_ms', '측정 흐름 평균 지연 (ms)'),
    ('allFlowsOnTimeRate', '참고: 전체 흐름 기한 내 도착률 (%)'),
]
OLD_PANELS = [   # 이전 형식 per_seed.csv (지표가 전체 흐름 합계, mainOnTimeRate 열이 있음)
    ('onTimeRate', '도착률 전체 (%)'),
    ('mainOnTimeRate', '도착률 흐름 0 (%)'),
    ('maxConsecLoss', '최대 연속 손실 (개)'),
    ('mainMaxConsecLoss', '흐름 0 최대 연속 손실 (개)'),
    ('burstPerMin', '1분당 연속 손실 (회)'),
    ('burstLenP95', '연속 손실 길이 95번째 백분위 (개)'),
]
ROUTE_LABEL = {'routeA': 'A', 'routeB': 'B', 'routeC': 'C'}
ROUTE_COLOR = {'routeA': '#2a78d6', 'routeB': '#7f7f7f', 'routeC': '#e377c2'}
LEVEL_ORDER = ['base', 'high', 'severe']


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def seed_values(rows, col):
    # 평가 시드별 값 (C 모델 여러 개면 시드마다 모델 평균)
    bySeed = {}
    for r in rows:
        if r.get(col, '') == '':
            continue
        bySeed.setdefault(r['seed'], []).append(float(r[col]))
    return np.array([np.mean(v) for _, v in sorted(bySeed.items(), key=lambda kv: int(kv[0]))])


def plot_eval(evalDir):
    rows = read_csv(os.path.join(evalDir, 'per_seed.csv'))
    levels = sorted({r['level'] for r in rows}, key=lambda x: LEVEL_ORDER.index(x) if x in LEVEL_ORDER else 99)
    routes = sorted({r['route'] for r in rows})
    seeds = sorted({int(r['seed']) for r in rows})
    nModels = len({r['cRun'] for r in rows if r['route'] == 'routeC'})
    panels = [(c, t) for c, t in (OLD_PANELS if 'mainOnTimeRate' in rows[0] else PANELS) if c in rows[0]]

    C = viz_colors()
    use_korean_font(C)
    ncol = 3
    nrow = (len(panels) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(16, 4.6 * nrow), squeeze=False)
    fig.patch.set_facecolor('white')
    width = 0.8 / len(routes)
    x = np.arange(len(levels))
    for ax, (col, title) in zip(axes.flat, panels):
        for k, route in enumerate(routes):
            means, stds = [], []
            for lv in levels:
                v = seed_values([r for r in rows if r['level'] == lv and r['route'] == route], col)
                means.append(v.mean() if len(v) else np.nan)
                stds.append(v.std(ddof=1) if len(v) > 1 else 0)
            pos = x + (k - (len(routes) - 1) / 2) * width
            ax.bar(pos, means, width, color=ROUTE_COLOR.get(route, C.series[k % 4]), label=ROUTE_LABEL.get(route, route))
            ax.errorbar(pos, means, yerr=stds, fmt='none', ecolor='black', capsize=3, lw=1)
            for p, m in zip(pos, means):
                if np.isfinite(m):
                    ax.text(p, m, f'{m:.0f}' if abs(m) >= 10 else f'{m:.1f}', ha='center', va='bottom', fontsize=9)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(levels)
        if '%' in title:
            ax.set_ylim(0, 105)
        ax.grid(axis='y', color=C.grid, lw=0.8)
        ax.set_axisbelow(True)
    for ax in list(axes.flat)[len(panels):]:
        ax.axis('off')
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', ncol=len(routes), frameon=False, fontsize=11)
    cNote = f', C는 학습 시드 {nModels}개 모델 평균' if nModels > 1 else ''
    fig.suptitle(f'최종 평가: {" vs ".join(ROUTE_LABEL.get(r, r) for r in routes)} '
                 f'(평가 시드 {seeds[0]}~{seeds[-1]}{cNote}, 막대 위 숫자는 평균, 선은 평가 시드 간 표준편차)', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = os.path.join(evalDir, 'eval_compare.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('사용법: python viz/plot_eval.py 평가폴더')
        sys.exit(1)
    print(f'저장: {plot_eval(os.path.expanduser(sys.argv[1]))}')
