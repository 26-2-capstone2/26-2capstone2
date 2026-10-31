# 강화학습 결과 그림 - 학습 곡선 (C가 배우긴 했나?), 라우팅 비교 막대 (C가 다른 방법보다 잘하나?)
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python viz/plot_rl.py 학습폴더 평가summary.csv [기존ABD_summary.csv]
#   예) python viz/plot_rl.py C:/Users/eun/rl_models/routeC_2026-10-30
#              C:/Users/eun/isl_saved_runs/eval_2026-10-30/summary.csv
#              C:/Users/eun/isl_saved_runs/compare_ABD_deadline70_2026-10-30/summary.csv
# 저장: 학습폴더/learning_curve.png, 평가폴더/route_compare.png
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_6x6_routing_py를 import 경로에 추가

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from viz.viz_colors import use_korean_font, viz_colors

LEVELS = ['base', 'high', 'severe']
LEVEL_LABELS = {'base': '기본 (base)', 'high': '높음 (high)', 'severe': '매우 높음 (severe)'}
ROUTES = ['routeA', 'routeB', 'routeC']
ROUTE_LABELS = {'routeA': 'A 최단 경로', 'routeB': 'B DRA', 'routeC': 'C 강화학습'}


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def style_axis(ax, C):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(C.axis)
    ax.tick_params(colors=C.muted, labelsize=9)
    ax.grid(axis='y', color=C.grid, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_learning_curve(trainDir, C):
    # 에피소드별 도착률 / 최대 연속 손실 / ε (세 그래프, 가로축 공유, 혼잡 단계별 선)
    rows = read_csv(os.path.join(trainDir, 'train_log.csv'))
    ep = np.array([int(r['episode']) for r in rows])
    lv = np.array([r['level'] for r in rows])
    onTime = np.array([float(r['onTimeRate']) for r in rows])
    consec = np.array([int(r['maxConsecLoss']) for r in rows])
    eps = np.array([float(r['epsilon']) for r in rows])

    fig, axes = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True, gridspec_kw=dict(height_ratios=[3, 3, 1.4]))
    fig.patch.set_facecolor('white')
    for i, level in enumerate(LEVELS):
        m = lv == level
        kw = dict(color=C.series[i], linewidth=2, marker='o', markersize=4, label=LEVEL_LABELS[level])
        axes[0].plot(ep[m], onTime[m], **kw)
        axes[1].plot(ep[m], consec[m], **kw)
    axes[2].plot(ep, eps, color=C.muted, linewidth=2)

    axes[0].set_ylabel('기한 내 도착률 (%)', color=C.text)
    axes[0].set_ylim(0, 102)
    axes[0].set_title('학습 곡선: 에피소드가 지날수록 C가 배우는지 (학습 시드 1001~, ε 탐험 포함)',
                      loc='left', color=C.text, fontsize=12)
    axes[0].legend(frameon=False, fontsize=9, loc='lower right')
    axes[1].set_ylabel('최대 연속 손실 (개)', color=C.text)
    axes[1].set_ylim(bottom=0)
    axes[2].set_ylabel('ε (무작위 비율)', color=C.text)
    axes[2].set_ylim(0, 1.05)
    axes[2].set_xlabel('에피소드 (30초짜리, 혼잡 단계를 돌아가며)', color=C.text)
    for ax in axes:
        style_axis(ax, C)

    fig.tight_layout()
    out = os.path.join(trainDir, 'learning_curve.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_route_compare(evalCsv, abdCsv, C):
    # 혼잡 단계별 A, B, C, D 손실률 / 최대 연속 손실 (두 그래프, 막대 묶음)
    rows = read_csv(evalCsv) + (read_csv(abdCsv) if abdCsv else [])
    val = {(r['level'], r['route']): r for r in rows}
    routes = [r for r in ROUTES if any((lv, r) in val for lv in LEVELS)]

    metrics = [('lossRate', '손실률 (%)', '{:.2f}%'), ('maxConsecLoss', '최대 연속 손실 (개)', '{:.0f}')]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor('white')
    x = np.arange(len(LEVELS))
    width = 0.8 / len(routes)
    for ax, (key, label, fmt) in zip(axes, metrics):
        for i, route in enumerate(routes):
            ys = [float(val[(lv, route)][key]) if (lv, route) in val else np.nan for lv in LEVELS]
            pos = x - 0.4 + width * (i + 0.5)
            ax.bar(pos, ys, width=width - 0.02, color=C.series[ROUTES.index(route)], label=ROUTE_LABELS[route],
                   edgecolor='white', linewidth=1)
            if route == 'routeC':   # C만 값 표시
                for px, y in zip(pos, ys):
                    ax.annotate(fmt.format(y), (px, y), xytext=(0, 3), textcoords='offset points',
                                ha='center', fontsize=8, color=C.text, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS], color=C.text)
        ax.set_title(f'{label}: 낮을수록 좋음', loc='left', color=C.text, fontsize=12)
        style_axis(ax, C)
    axes[0].legend(frameon=False, fontsize=9, loc='upper left')
    fig.suptitle('라우팅 비교 (평가 시드 1~20, 30초 x 20 에피소드, 기한 70)', x=0.01, ha='left', color=C.muted, fontsize=10)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(evalCsv), 'route_compare.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == '__main__':
    C = viz_colors()
    use_korean_font(C)
    args = sys.argv[1:]
    print(plot_learning_curve(args[0], C))
    print(plot_route_compare(args[1], args[2] if len(args) > 2 else None, C))
