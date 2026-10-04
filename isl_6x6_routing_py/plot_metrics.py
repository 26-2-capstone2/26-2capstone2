# 지표 비교 그래프 저장 - 지표 7개를 실행(알고리즘·ε)별 막대로 비교 (지표마다 그래프 1개)
#
import matplotlib.pyplot as plt
import numpy as np

from viz_colors import use_korean_font, viz_colors


def plot_metrics(T, P, pngPath):
    # T: compute_metrics 결과 표 (열 이름 -> 값 배열, 실행 1회 = 1줄)
    # 나중에 강화학습 결과를 T에 한 줄 추가하면 막대가 하나 늘어나는 구조
    C = viz_colors()
    use_korean_font(C)
    fig, axs = plt.subplots(2, 4, figsize=(15, 6.8), constrained_layout=True)
    axs = axs.ravel()

    vars_ = ['avgLatency_ms', 'lossRate', 'throughput_Mbps', 'onTimeRate',
             'maxConsecLoss', 'routeChanges', 'avgHops']
    names = ['Average Latency (ms)', 'Packet Loss Rate', 'Throughput (Mbps)',
             'On-time Delivery Rate', 'Consecutive Packet Loss Length',
             'Route Change Count', 'Average Hop Count']
    fmt = ['{:.1f}', '{:.4f}', '{:.4f}', '{:.4f}', '{:d}', '{:d}', '{:.2f}']

    labels = run_labels(T)
    n = len(labels)
    for i, var in enumerate(vars_):
        ax = axs[i]
        vals = np.asarray(T[var])
        x = np.arange(1, n + 1)
        ax.bar(x, vals, 0.55, color=C.series[:n])
        style_axes(ax, C)
        ax.set_xticks(x, labels)
        ax.set_title(names[i], color=C.text)
        top = vals.max()
        ax.set_ylim(0, 1 if top <= 0 else top * 1.25)   # 전부 0이면 축을 0~1로 고정
        for j in range(n):
            v = int(vals[j]) if fmt[i] == '{:d}' else vals[j]
            ax.text(x[j], vals[j], fmt[i].format(v), ha='center', va='bottom', color=C.text, fontsize=10)

    # 실행 정보
    ax = axs[7]
    ax.axis('off')
    info = '\n'.join([
        '실행 조건',
        f'Grid {P.numPlanes} x {P.satsPerPlane},  ({P.srcSat[0]},{P.srcSat[1]}) → ({P.dstSat[0]},{P.dstSat[1]})',
        f'1초마다 생성: {P.genRate}개,  패킷 {P.packetSize} Byte',
        f'총 시간: {P.simTime * P.stepTime:.0f}초 ({P.simTime} step)',
        f'생성 패킷: {int(T["generated"][0])}개 / 실행',
        f'B 라우팅: k = {P.k:.1f}, X = {P.X:.1f}, Y = {P.Y:.1f}',
        f'기한 {P.deadline} ms,  TTL {P.ttlInit}',
    ])
    ax.text(0, 1, info, va='top', fontsize=11, color=C.text, linespacing=1.6)

    fig.suptitle('성능 지표 비교', fontsize=15, color=C.text)
    fig.savefig(pngPath, dpi=120, facecolor='w')
    plt.close(fig)


def run_labels(T):
    return [f'B (ε = {e:.1f})' for e in T['epsilon']]


def style_axes(ax, C):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(C.axis)
    ax.tick_params(colors=C.axis, length=0)
    ax.grid(axis='y', color=C.grid)
    ax.set_axisbelow(True)
