# 실행 분석 그래프 저장 - 한 번의 실행 안에서 지연 분포, 시간 변화, 링크 사용량, 홉 수, 선택 유형, 손실 원인을 보여줌
#
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable

from run_isl_sim import ROUTE_LABELS
from viz_colors import use_korean_font, viz_colors


def plot_analysis(Rs, P, pngPath):
    # Rs: run_isl_sim 결과들 (list, 실행 1회 = 1칸)
    C = viz_colors()
    use_korean_font(C)
    lineStyles = ['-', '--', ':', '-.']   # 선이 겹쳐도 구분되도록 실행마다 선 모양도 다르게
    nRun = len(Rs)
    labels = [f'{ROUTE_LABELS[R.routeName][0]} (ε = {R.epsilon:.1f})' for R in Rs]

    fig, axs = plt.subplots(2, 4, figsize=(17, 8.2), constrained_layout=True)
    axs = axs.ravel()

    # ---- 1. 패킷별 지연 분포 ----
    ax = axs[0]
    edges = np.arange(0, P.deadline + 21, 1)
    for r, R in enumerate(Rs):
        reached = (R.status == 1) | (R.status == 2)
        lat = (R.endTime[reached] - R.genTime[reached]) * P.stepTime * 1e3
        w = np.ones(len(lat)) / max(len(lat), 1)
        ax.hist(lat, edges, weights=w, histtype='step', color=C.series[r], linewidth=2,
                linestyle=lineStyles[r], label=labels[r])
    ax.axvline(P.deadline, linestyle='--', color=C.muted)
    ax.text(P.deadline, ax.get_ylim()[1] * 0.5, ' 기한', color=C.muted, rotation=90, va='center')
    style_axes(ax, C)
    ax.set_xlim(30, P.deadline + 20)
    ax.set_xlabel('지연 (ms)'); ax.set_ylabel('패킷 비율')
    ax.set_title('패킷별 지연 분포')
    ax.legend(loc='upper right', frameon=False)

    # ---- 2, 3. 시간에 따른 변화 (10초 단위) ----
    win = round(10 / P.stepTime)
    nWin = int(np.ceil(P.simTime / win))
    tMid = (np.arange(1, nWin + 1) - 0.5) * win * P.stepTime
    onTimeW = np.full((nRun, nWin), np.nan)
    latW = np.full((nRun, nWin), np.nan)
    for r, R in enumerate(Rs):
        w = np.minimum(np.ceil(R.genTime / win).astype(int), nWin) - 1
        reached = (R.status == 1) | (R.status == 2)
        lat = (R.endTime - R.genTime) * P.stepTime * 1e3
        cnt = np.bincount(w, minlength=nWin)
        onTimeW[r] = np.where(cnt > 0, np.bincount(w, weights=(R.status == 1), minlength=nWin) / np.maximum(cnt, 1), np.nan)
        cntR = np.bincount(w[reached], minlength=nWin)
        latW[r] = np.where(cntR > 0, np.bincount(w[reached], weights=lat[reached], minlength=nWin) / np.maximum(cntR, 1), np.nan)

    ax = axs[1]
    for r in range(nRun):
        ax.plot(tMid, onTimeW[r], lineStyles[r], color=C.series[r], linewidth=2.5 - 0.5 * r, label=labels[r])
    style_axes(ax, C)
    ax.set_ylim(max(0, np.nanmin(onTimeW) - 0.05), 1.01)
    ax.set_xlabel('시간 (s)'); ax.set_ylabel('기한 내 도착률')
    ax.set_title('기한 내 도착률 (10초 단위)')
    ax.legend(loc='lower left', frameon=False)

    ax = axs[2]
    for r in range(nRun):
        ax.plot(tMid, latW[r], lineStyles[r], color=C.series[r], linewidth=2.5 - 0.5 * r, label=labels[r])
    ax.axhline(P.deadline, linestyle='--', color=C.muted)
    ax.text(tMid[-1], P.deadline, '기한', color=C.muted, ha='right', va='bottom')
    style_axes(ax, C)
    ax.set_ylim(0, P.deadline * 1.1)
    ax.set_xlabel('시간 (s)'); ax.set_ylabel('평균 지연 (ms)')
    ax.set_title('평균 지연 (10초 단위)')
    ax.legend(loc='lower left', frameon=False)

    # ---- 4. 홉 수 분포 ----
    ax = axs[3]
    reachedHops = [R.hops[(R.status == 1) | (R.status == 2)] for R in Rs]
    hopVals = np.arange(min(h.min() for h in reachedHops), max(h.max() for h in reachedHops) + 1)
    width = 0.8 / nRun
    for r in range(nRun):
        counts = np.array([(reachedHops[r] == h).sum() for h in hopVals]) / len(reachedHops[r])
        ax.bar(hopVals + (r - (nRun - 1) / 2) * width, counts, width, color=C.series[r], label=labels[r])
    style_axes(ax, C)
    ax.grid(axis='x', visible=False)
    ax.set_xticks(hopVals)
    ax.set_xlabel('홉 수 (최소 경로 = 10)'); ax.set_ylabel('도착 패킷 비율')
    ax.set_title('홉 수 분포')
    ax.legend(loc='upper right', frameon=False)

    # ---- 5, 6. 링크 사용량 지도 (실행별) ----
    for r in range(min(nRun, 2)):
        draw_link_usage(axs[4 + r], Rs[r], P, C, fig)
        axs[4 + r].set_title(f'링크 사용량: {labels[r]}')

    # ---- 7. 선택 유형 비율 ----
    ax = axs[6]
    typeNames = ['주 경로', '대체 경로', '우회', '무작위']
    share = np.zeros((nRun, 4))
    for r, R in enumerate(Rs):
        ct = R.decisionLog[:, 22]
        share[r] = [(ct == k).sum() / len(ct) * 100 for k in range(1, 5)]
    left = np.zeros(nRun)
    y = np.arange(1, nRun + 1)
    for k in range(4):
        ax.barh(y, share[:, k], 0.5, left=left, color=C.series[k], edgecolor='w', linewidth=1.5, label=typeNames[k])
        left += share[:, k]
    style_axes(ax, C)
    ax.grid(axis='y', visible=False); ax.grid(axis='x', color=C.grid)
    ax.set_yticks(y, labels); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel('라우팅 결정 비율 (%)')
    ax.set_title('선택 유형')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=4, frameon=False)
    for r in range(nRun):
        ax.text(1, y[r], f'주 {share[r, 0]:.1f}%', color='w', fontsize=9, va='center')

    # ---- 8. 손실 원인 ----
    ax = axs[7]
    lossNames = ['목적지 기한 초과', '중간 기한 초과', '큐 오버플로', 'TTL 만료']
    lossCnt = np.array([[(R.status == s).sum() for s in (2, 3, 4, 5)] for R in Rs])
    bottom = np.zeros(nRun)
    x = np.arange(1, nRun + 1)
    for k in range(4):
        ax.bar(x, lossCnt[:, k], 0.5, bottom=bottom, color=C.series[k], edgecolor='w', linewidth=1.5, label=lossNames[k])
        bottom += lossCnt[:, k]
    style_axes(ax, C)
    ax.grid(axis='x', visible=False)
    ax.set_xticks(x, labels)
    ax.set_ylabel('손실 패킷 수')
    total = lossCnt.sum(axis=1)
    ax.set_ylim(0, max(total.max(), 1) * 1.25)
    for r in range(nRun):
        ax.text(x[r], total[r], f'{total[r]}개', ha='center', va='bottom', color=C.text)
    if np.all(total == 0):
        ax.text(np.mean([1, nRun]), 0.5, '손실 없음', ha='center', color=C.muted, fontsize=12)
    ax.set_title('손실 원인')
    ax.legend(loc='upper left', frameon=False)

    fig.suptitle(f'실행 분석 (1초마다 {P.genRate}개 생성, {P.simTime * P.stepTime:.0f}초)', fontsize=15, color=C.text)
    fig.savefig(pngPath, dpi=120, facecolor='w')
    plt.close(fig)


def draw_link_usage(ax, R, P, C, fig):
    # 결정 기록에서 링크별로 지나간 패킷 수를 세서 Grid 위에 색으로 표시
    G = R.grid
    D = R.decisionLog[R.decisionLog[:, 23] == 1, :]
    link = G.linkId[D[:, 3].astype(int), D[:, 4].astype(int), D[:, 21].astype(int) - 1]
    use = np.bincount(link, minlength=G.numLinks)
    maxUse = use.max()

    ax.set_aspect('equal'); ax.axis('off')
    ax.set_xlim(-0.6, P.numPlanes - 0.4); ax.set_ylim(-(P.satsPerPlane - 1) - 0.6, 0.6)
    cmap = LinearSegmentedColormap.from_list('use', [C.seqLow, C.seqHigh])
    for l in np.flatnonzero(G.nextP >= 0):
        p, s, d0 = np.unravel_index(l, G.hasLink.shape, order='F')
        u = np.array([G.stepP[d0], -G.stepS[d0]])
        off = 0.07 * np.array([-u[1], u[0]])
        a = np.array([p, -s])
        b0 = a + 0.2 * u + off
        b1 = a + 0.8 * u + off
        if use[l] == 0:
            ax.plot([b0[0], b1[0]], [b0[1], b1[1]], '-', color=C.unused, linewidth=1.5)
        else:
            ax.plot([b0[0], b1[0]], [b0[1], b1[1]], '-', color=cmap(use[l] / maxUse), linewidth=4)
    PP, SS = np.meshgrid(np.arange(P.numPlanes), np.arange(P.satsPerPlane), indexing='ij')
    ax.scatter(PP.ravel(), -SS.ravel(), 70, color='w', edgecolors=C.axis, zorder=3)
    ax.scatter(P.srcSat[0], -P.srcSat[1], 110, color=C.series[0], zorder=4)
    ax.scatter(P.dstSat[0], -P.dstSat[1], 110, color=C.series[1], zorder=4)
    ax.text(P.srcSat[0], -P.srcSat[1] + 0.35, '출발', ha='center', fontsize=9)
    ax.text(P.dstSat[0], -P.dstSat[1] - 0.35, '도착', ha='center', va='top', fontsize=9)
    cb = fig.colorbar(ScalarMappable(norm=Normalize(0, maxUse), cmap=cmap), ax=ax, shrink=0.8)
    cb.set_label('지나간 패킷 수', color=C.muted)


def style_axes(ax, C):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(C.axis)
    ax.tick_params(colors=C.axis, length=0)
    ax.grid(color=C.grid)
    ax.set_axisbelow(True)
