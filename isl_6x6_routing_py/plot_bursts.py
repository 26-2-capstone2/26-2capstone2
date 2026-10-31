# 연속 손실 분석 그래프 저장 - 손실 구간 길이별 손실 패킷 수, 연속 손실 발생 시각, 연속/단발 손실 원인, 에피소드별 연속 손실 횟수
#
# 연속 손실 = 패킷 번호 순서로 손실이 P.burstMinLen개(기본 3개) 이상 이어진 구간 (burst_loss.py)
import matplotlib.pyplot as plt
import numpy as np

from burst_loss import LOSS_CODES, burst_info
from run_isl_sim import ROUTE_LABELS
from viz_colors import use_korean_font, viz_colors

LOSS_NAMES = ['목적지 기한 초과', '중간 기한 초과', '큐 오버플로', 'TTL 만료']   # LOSS_CODES 2, 3, 4, 5 순서
MARKERS = ['o', 's', '^', 'D']


def plot_bursts(Rs, P, pngPath):
    # Rs: merge_episodes 결과들 (실행 1회 = 1칸), P: 후처리용 설정 (episodes.total_params)
    C = viz_colors()
    use_korean_font(C)
    nRun = len(Rs)
    labels = [f'{ROUTE_LABELS[R.routeName][0]} (ε = {R.epsilon:.1f})' for R in Rs]
    Bs = [burst_info(R, P) for R in Rs]
    m = Bs[0].minLen

    fig, axs = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    axs = axs.ravel()

    # ---- 1. 손실 구간 길이별 손실 패킷 수 (길이 1~minLen-1은 단발, minLen 이상은 연속 손실) ----
    #   구간 수가 아니라 패킷 수로 세서 '손실 패킷 중 얼마가 몰려서 났는지'가 보이게 함 (길이 L 구간 1개 = 패킷 L개)
    ax = axs[0]
    cap = 20                                     # 이 길이 이상은 한 칸으로 묶음
    xs = np.arange(1, cap + 1)
    width = 0.8 / nRun
    for r, B in enumerate(Bs):
        pk = np.bincount(np.minimum(B.runLen, cap), weights=B.runLen, minlength=cap + 1)[1:]
        share = pk[m - 1:].sum() / max(pk.sum(), 1) * 100
        ax.bar(xs + (r - (nRun - 1) / 2) * width, pk, width, color=C.series[r],
               label=f'{labels[r]}: 연속 손실 비중 {share:.1f}%')
    ax.axvspan(m - 0.5, cap + 0.5, color=C.grid, alpha=0.6, zorder=0)
    ax.text(m - 0.3, 0.78, f'연속 손실\n(≥{m}개)', color=C.muted, va='top', transform=ax.get_xaxis_transform())
    style_axes(ax, C)
    ax.set_xticks(xs, [str(x) if x < cap else f'{cap}+' for x in xs])
    ax.set_xlim(0.4, cap + 0.6)
    ax.set_xlabel('손실 구간 길이 (연달아 잃은 패킷 수)'); ax.set_ylabel('손실 패킷 수')
    ax.set_title('손실 구간 길이별 손실 패킷 수')
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
    ax.legend(loc='upper center', ncol=2, fontsize=9, frameon=False)

    # ---- 2. 연속 손실 발생 시각과 길이 ----
    ax = axs[1]
    epLen = getattr(P, 'episodeLen', P.simTime)
    for e in range(1, int(round(P.simTime / epLen))):
        ax.axvline(e * epLen * P.stepTime, color=C.axis, linewidth=0.6, linestyle=':', zorder=0)
    for r, B in enumerate(Bs):
        T = B.table
        ax.scatter(T[:, 5] * P.stepTime, T[:, 4], 28, marker=MARKERS[r % 4], facecolors='none',
                   edgecolors=C.series[r], linewidths=1.3, label=f'{labels[r]}: {len(T)}번')
    style_axes(ax, C)
    ax.set_xlim(0, P.simTime * P.stepTime)
    ax.set_ylim(m - 0.5, max([int(B.table[:, 4].max()) if len(B.table) else m for B in Bs]) + 1)
    ax.set_xlabel('시간 (s, 점선 = 에피소드 경계)'); ax.set_ylabel('연속 손실 길이 (패킷)')
    ax.set_title(f'연속 손실 (≥{m}개) 발생 시각과 길이')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False)

    # ---- 3. 손실 원인: 연속 손실 안 vs 단발 손실 ----
    ax = axs[2]
    x, xl = [], []
    vals = []
    for r, (R, B) in enumerate(zip(Rs, Bs)):
        lost = R.status != 1
        inBurst = B.pktBurstId >= 0
        for k, (sel, name) in enumerate([(lost & inBurst, '연속'), (lost & ~inBurst, '단발')]):
            x.append(r * 2.6 + k * 1.1)
            xl.append(f'{labels[r]}\n{name}')
            vals.append([int((R.status[sel] == c).sum()) for c in LOSS_CODES])
    vals = np.array(vals)
    bottom = np.zeros(len(x))
    for k in range(4):
        ax.bar(x, vals[:, k], 0.9, bottom=bottom, color=C.series[k], edgecolor='w', linewidth=1.5, label=LOSS_NAMES[k])
        bottom += vals[:, k]
    for i in range(len(x)):
        ax.text(x[i], bottom[i], f'{int(bottom[i])}개', ha='center', va='bottom', color=C.text, fontsize=9)
    style_axes(ax, C)
    ax.grid(axis='x', visible=False)
    ax.set_xticks(x, xl, fontsize=9)
    ax.set_ylim(0, max(bottom.max(), 1) * 1.15)
    ax.set_ylabel('손실 패킷 수')
    ax.set_title(f'손실 원인: 연속 손실(≥{m}개) 안 vs 단발 손실(1~{m - 1}개)')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=4, frameon=False)

    # ---- 4. 에피소드별 연속 손실 횟수 (에피소드마다 핫스팟 시나리오가 다름) ----
    ax = axs[3]
    nEp = int(max(R.numEpisodes if hasattr(R, 'numEpisodes') else 1 for R in Rs))
    eps = np.arange(nEp)
    for r, B in enumerate(Bs):
        cnt = np.bincount(B.table[:, 1], minlength=nEp)[:nEp] if len(B.table) else np.zeros(nEp)
        ax.bar(eps + (r - (nRun - 1) / 2) * width, cnt, width, color=C.series[r], label=labels[r])
    style_axes(ax, C)
    ax.grid(axis='x', visible=False)
    ax.set_xticks(eps)
    ax.set_xlabel('에피소드 (핫스팟 시나리오, bg_scenario.csv 참고)'); ax.set_ylabel('연속 손실 횟수')
    ax.set_title(f'에피소드별 연속 손실 (≥{m}개) 횟수')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False)

    fig.suptitle(f'연속 손실 분석 (패킷 번호 순서로 {m}개 이상 연달아 손실, 1초마다 {P.genRate}개 생성, '
                 f'{P.simTime * P.stepTime:.0f}초)', fontsize=15, color=C.text)
    fig.savefig(pngPath, dpi=120, facecolor='w')
    plt.close(fig)


def style_axes(ax, C):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(C.axis)
    ax.tick_params(colors=C.axis, length=0)
    ax.grid(axis='y', color=C.grid)
    ax.set_axisbelow(True)
