# 강화학습 결과 그림 - 학습 곡선 (C가 배우긴 했나?), 라우팅 비교 막대 (C가 다른 방법보다 잘하나?)
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python viz/plot_rl.py 학습폴더 평가summary.csv [평가summary.csv ...]
#   예) python viz/plot_rl.py C:/Users/eun/rl_models/routeC_2026-11-01
#              C:/Users/eun/isl_saved_runs/eval_2026-11-01/summary.csv
#   평가를 혼잡 단계나 라우팅별로 나눠 돌렸다면 summary.csv를 여러 개 주면 합쳐서 그림
# 저장: 학습폴더/learning_curve.png, 첫 평가폴더/route_compare.png
import re
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
ROUTE_LABELS = {'routeA': 'A Dijkstra', 'routeB': 'B DRA', 'routeC': 'C 강화학습'}


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
    bursts = np.array([int(r['burstCount']) for r in rows])
    eps = np.array([float(r['epsilon']) for r in rows])

    fig, axes = plt.subplots(4, 1, figsize=(9, 10.5), sharex=True, gridspec_kw=dict(height_ratios=[3, 3, 3, 1.4]))
    fig.patch.set_facecolor('white')
    for i, level in enumerate(LEVELS):
        m = lv == level
        kw = dict(color=C.series[i], linewidth=2, marker='o', markersize=4, label=LEVEL_LABELS[level])
        axes[0].plot(ep[m], onTime[m], **kw)
        axes[1].plot(ep[m], consec[m], **kw)
        axes[2].plot(ep[m], bursts[m], **kw)
    axes[3].plot(ep, eps, color=C.muted, linewidth=2)

    axes[0].set_ylabel('기한 내 도착률 (%)', color=C.text)
    axes[0].set_ylim(0, 102)
    axes[0].set_title('학습 곡선',
                      loc='left', color=C.text, fontsize=12)
    axes[0].legend(frameon=False, fontsize=9, loc='lower right')
    axes[1].set_ylabel('최대 연속 손실 (개)', color=C.text)
    axes[1].set_ylim(bottom=0)
    axes[2].set_ylabel('연속 손실 횟수 (번)', color=C.text)
    axes[2].set_ylim(bottom=0)
    axes[3].set_ylabel('ε (무작위 비율)', color=C.text)
    axes[3].set_ylim(0, 1.05)
    axes[3].set_xlabel('에피소드(30초, 혼잡 3단계)', color=C.text)
    for ax in axes:
        style_axis(ax, C)

    fig.tight_layout()
    out = os.path.join(trainDir, 'learning_curve.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def eval_condition(evalCsv):
    # 평가 폴더의 run_info.txt에서 평가 시드와 에피소드 수를 읽음 (그림 제목용)
    info = os.path.join(os.path.dirname(evalCsv), 'run_info.txt')
    if os.path.exists(info):
        m = re.search(r'평가 시드 (\d+)~(\d+) \(에피소드 (\d+)개', open(info, encoding='utf-8').read())
        if m:
            return f'평가 시드 {m.group(1)}~{m.group(2)}, 30초 x {m.group(3)} 에피소드'
    return '평가 시드 1~20, 30초 x 20 에피소드'


def plot_route_compare(evalCsvs, C):
    # 혼잡 단계별 A, B, C 비교 (연속 손실 지표 먼저, 도착률은 확인용)
    rows = [r for path in evalCsvs for r in read_csv(path)]
    val = {(r['level'], r['route']): r for r in rows}
    routes = [r for r in ROUTES if any((lv, r) in val for lv in LEVELS)]

    metrics = [('maxConsecLoss', '최대 연속 손실 (개)', '{:.0f}', '낮을수록 좋음'),
               ('burstCount', '연속 손실 횟수 (번)', '{:.0f}', '낮을수록 좋음'),
               ('runs_ge5', '5개 이상 연속 손실 (번)', '{:.0f}', '낮을수록 좋음'),
               ('onTimeRate', '기한 내 도착률 (%)', '{:.2f}', '높을수록 좋음')]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.patch.set_facecolor('white')
    x = np.arange(len(LEVELS))
    width = 0.8 / len(routes)
    for ax, (key, label, fmt, better) in zip(axes.flat, metrics):
        for i, route in enumerate(routes):
            ys = [float(val[(lv, route)][key]) if (lv, route) in val else np.nan for lv in LEVELS]
            pos = x - 0.4 + width * (i + 0.5)
            ax.bar(pos, ys, width=width - 0.02, color=C.series[ROUTES.index(route)], label=ROUTE_LABELS[route],
                   edgecolor='white', linewidth=1)
            for px, y in zip(pos, ys):
                if not np.isnan(y):
                    ax.annotate(fmt.format(y), (px, y), xytext=(0, 3), textcoords='offset points',
                                ha='center', fontsize=7.5, color=C.text,
                                fontweight='bold' if route == 'routeC' else 'normal')
        ax.set_xticks(x)
        ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS], color=C.text)
        ax.set_title(label, loc='left', color=C.text, fontsize=12)
        if key == 'onTimeRate':
            low = min(float(r['onTimeRate']) for r in rows)
            ax.set_ylim(max(0, low - 3), 102)
        style_axis(ax, C)
    axes.flat[0].legend(frameon=False, fontsize=9, loc='upper left')
    fig.suptitle(f'라우팅 비교 ({eval_condition(evalCsvs[0])}, 기한 70)', x=0.01, ha='left', color=C.muted, fontsize=10)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(evalCsvs[0]), 'route_compare.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == '__main__':
    C = viz_colors()
    use_korean_font(C)
    args = sys.argv[1:]
    print(plot_learning_curve(args[0], C))
    if len(args) > 1:
        print(plot_route_compare(args[1:], C))
