# 애니메이션 저장 - 링크 큐 점유율과 패킷 이동을 GIF로 만듦
#
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
from PIL import Image

from viz_colors import use_korean_font, viz_colors


def animate_run(R, P, gifPath):
    # 시뮬레이션 1회를 GIF 애니메이션으로 저장
    # 왼쪽: Grid 링크 큐 점유율(색) + 링크 위 전송 중 패킷(점)
    # 오른쪽 위: 누적 생성/도착/손실, 오른쪽 아래: 출발 위성 링크 큐 길이
    C = viz_colors()
    use_korean_font(C)
    G = R.grid
    animSteps = R.animQueue.shape[1]

    fig = plt.figure(figsize=(12, 6.2), facecolor='w')

    # ---- Grid ----
    ax = fig.add_axes([0.02, 0.06, 0.5, 0.84])
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_xlim(-0.7, P.numPlanes - 0.3)
    ax.set_ylim(-(P.satsPerPlane - 1) - 0.7, 0.7)

    cmap = LinearSegmentedColormap.from_list('q', [(0, '#d9d9d9'), (0.02, '#4dbf4d'), (0.5, '#ffcc00'),
                                                   (0.8, '#ff7300'), (1, '#d91a1a')])
    valid = np.flatnonzero(G.nextP >= 0)
    hL = []
    mid = np.zeros((len(valid), 2))
    for i, l in enumerate(valid):
        p, s, d0 = np.unravel_index(l, G.hasLink.shape, order='F')
        u = np.array([G.stepP[d0], -G.stepS[d0]])
        off = 0.07 * np.array([-u[1], u[0]])
        a = np.array([p, -s])
        b0 = a + 0.2 * u + off
        b1 = a + 0.8 * u + off
        hL.append(ax.plot([b0[0], b1[0]], [b0[1], b1[1]], '-', linewidth=4, color=cmap(0.0))[0])
        mid[i] = a + 0.55 * u + off

    PP, SS = np.meshgrid(np.arange(P.numPlanes), np.arange(P.satsPerPlane), indexing='ij')
    ax.scatter(PP.ravel(), -SS.ravel(), 260, color='#cce0ff', edgecolors='#667fb3', zorder=3)
    ax.scatter(P.srcSat[0], -P.srcSat[1], 320, color='#3399ff', edgecolors='k', zorder=4)
    ax.scatter(P.dstSat[0], -P.dstSat[1], 320, color='#ff6666', edgecolors='k', zorder=4)
    ax.text(P.srcSat[0], -P.srcSat[1] + 0.32, '출발', ha='center', fontsize=9)
    ax.text(P.dstSat[0], -P.dstSat[1] - 0.32, '도착', ha='center', va='top', fontsize=9)
    for p in range(P.numPlanes):
        ax.text(p, 0.5, f'p={p}', ha='center', fontsize=8, color='#666666')
    for s in range(P.satsPerPlane):
        ax.text(-0.55, -s, f's={s}', ha='center', va='center', fontsize=8, color='#666666')
    hF = ax.scatter([], [], 10, color='#1a1a73', zorder=5)
    cb = fig.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap=cmap), ax=ax, shrink=0.8)
    cb.set_label('링크 큐 점유율 (큐 길이 / 100)')
    hT = ax.set_title('', fontsize=12)

    # ---- 누적 패킷 수 ----
    ax2 = fig.add_axes([0.62, 0.57, 0.35, 0.33])
    timeline = R.timeline[:animSteps, :]
    lost = timeline[:, 2:6].sum(axis=1)
    hG, = ax2.plot([], [], 'k-', linewidth=1.5, label='생성')
    hO, = ax2.plot([], [], '-', color='#339933', linewidth=1.5, label='기한 내 도착')
    hX, = ax2.plot([], [], '-', color='#d91a1a', linewidth=1.5, label='손실')
    ax2.set_xlim(0, animSteps); ax2.set_ylim(0, max(timeline[-1, 0], 1) * 1.05)
    ax2.set_xlabel('step (ms)'); ax2.set_ylabel('누적 패킷 수')
    ax2.legend(loc='upper left'); ax2.grid(True)
    ax2.set_title('누적 패킷')

    # ---- 출발 위성 링크 큐 ----
    ax3 = fig.add_axes([0.62, 0.08, 0.35, 0.33])
    lR = G.linkId[G.srcSat[0], G.srcSat[1], 3]
    lD = G.linkId[G.srcSat[0], G.srcSat[1], 1]
    qR = R.animQueue[lR, :].astype(float)
    qD = R.animQueue[lD, :].astype(float)
    hR, = ax3.plot([], [], '-', color='#1a66cc', linewidth=1.5, label='우 (주 경로)')
    hDn, = ax3.plot([], [], '-', color='#e6801a', linewidth=1.5, label='하 (대체 경로)')
    ax3.axhline(P.queueMax, color='k', linestyle=':')
    ax3.set_xlim(0, animSteps); ax3.set_ylim(0, P.queueMax * 1.1)
    ax3.set_xlabel('step (ms)'); ax3.set_ylabel('큐 길이 (packets)')
    ax3.legend(loc='upper left'); ax3.grid(True)
    ax3.set_title('출발 위성 (0,0) 링크 큐')

    # ---- 프레임 ----
    frames = []
    for t in range(1, animSteps + 1, P.animFrameInterval):
        q = R.animQueue[valid, t - 1].astype(float) / P.queueMax
        for i in range(len(valid)):
            hL[i].set_color(cmap(q[i]))
        f = R.animInFlight[valid, t - 1].astype(float)
        on = f > 0
        hF.set_offsets(mid[on] if on.any() else np.empty((0, 2)))
        hF.set_sizes(12 + 5 * f[on])

        tt = np.arange(1, t + 1)
        hG.set_data(tt, timeline[:t, 0])
        hO.set_data(tt, timeline[:t, 1])
        hX.set_data(tt, lost[:t])
        hR.set_data(tt, qR[:t])
        hDn.set_data(tt, qD[:t])

        hT.set_text(f'B 라우팅 | 생성률 {R.genRate} packets/s, ε = {R.epsilon:.1f} | t = {t} ms')
        fig.canvas.draw()
        img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
        frames.append(Image.fromarray(img).quantize(colors=128))

    frames[0].save(gifPath, save_all=True, append_images=frames[1:], duration=80, loop=0)
    plt.close(fig)
