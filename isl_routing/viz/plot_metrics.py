# 지표 비교 그래프 저장 - 지표 11개(기본 7개 + 연속 손실 4개)를 실행(알고리즘·ε)별 막대로 비교 (지표마다 그래프 1개)
#
import matplotlib.pyplot as plt
import numpy as np

from sim.run_isl_sim import ROUTE_LABELS
from viz.viz_colors import use_korean_font, viz_colors


def plot_metrics(T, P, pngPath):
    # T: compute_metrics 결과 표 (열 이름 -> 값 배열, 실행 1회 = 1줄)
    # 나중에 강화학습 결과를 T에 한 줄 추가하면 막대가 하나 늘어나는 구조
    C = viz_colors()
    use_korean_font(C)
    fig, axs = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    axs = axs.ravel()

    # 1줄: 기본 지표, 2줄: 연속 손실 지표, 3줄: 연속 손실 비율 + 경로 지표 + 실행 정보
    m = int(getattr(P, 'burstMinLen', 3))
    vars_ = ['avgLatency_ms', 'lossRate', 'throughput_Mbps', 'onTimeRate',
             'maxConsecLoss', 'burstCount', 'avgBurstLen', 'burstLossRate',
             'burstShareOfLoss', 'routeChanges', 'avgHops']
    names = ['Average Latency (ms)', 'Packet Loss Rate', 'Throughput (Mbps)', 'On-time Delivery Rate',
             'Max Consecutive Loss Length', f'Consecutive Loss Count (≥{m})',
             f'Avg Consecutive Loss Length (≥{m})', f'Consecutive Loss Packet Rate (≥{m})',
             f'Share of Loss in Bursts (≥{m})', 'Route Change Count', 'Average Hop Count']
    fmt = ['{:.1f}', '{:.4f}', '{:.4f}', '{:.4f}',
           '{:d}', '{:d}', '{:.2f}', '{:.4f}',
           '{:.3f}', '{:d}', '{:.2f}']

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
    ax = axs[11]
    ax.axis('off')
    routeNames = list(dict.fromkeys(T['routeName']))   # 실행에 쓰인 라우팅 (순서 유지, 중복 제거)
    info = '\n'.join([
        '실행 조건',
        '라우팅: ' + ', '.join(ROUTE_LABELS[r] for r in routeNames),
        f'Grid {P.numPlanes} x {P.satsPerPlane},  ({P.srcSat[0]},{P.srcSat[1]}) → ({P.dstSat[0]},{P.dstSat[1]})',
        f'1초마다 생성: {P.genRate}개,  패킷 {P.packetSize} Byte',
        f'총 시간: {P.simTime * P.stepTime:.0f}초 ({P.simTime} step)'
        + (f' = {P.numEpisodes}에피소드 x {P.episodeLen * P.stepTime:.0f}초' if getattr(P, 'episodeLen', None) else ''),
        f'생성 패킷: {int(T["generated"][0])}개 / 실행',
    ] + ([f'B DRA: 혼잡 임계값 {P.draThreshold:.2f} x 큐 ({P.draThreshold * P.queueMax:.0f} packets)']
         if 'routeB' in routeNames else []) + [
        f'기한 {P.deadline} ms,  TTL {P.ttlInit}',
        f'연속 손실: 패킷 번호 순서로 {m}개 이상 연달아 손실',
    ])
    ax.text(0, 1, info, va='top', fontsize=11, color=C.text, linespacing=1.6)

    fig.suptitle('성능 지표 비교', fontsize=15, color=C.text)
    fig.savefig(pngPath, dpi=120, facecolor='w')
    plt.close(fig)


def run_labels(T):
    return [f'{ROUTE_LABELS[r][0]} (ε = {e:.1f})' for r, e in zip(T['routeName'], T['epsilon'])]


def style_axes(ax, C):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(C.axis)
    ax.tick_params(colors=C.axis, length=0)
    ax.grid(axis='y', color=C.grid)
    ax.set_axisbelow(True)
