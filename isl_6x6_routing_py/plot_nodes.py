# 노드 그래프 - node_log로 노드별 요약 지도(6x6)와 노드 1개의 시간 변화를 그림 (main_isl, show_node에서 사용)
#
import matplotlib.pyplot as plt
import numpy as np

from viz_colors import use_korean_font, viz_colors

DIRS = ['up', 'down', 'left', 'right']
DIRS_KO = ['상', '하', '좌', '우']


def node_columns(table, columns):
    # node_log 표(배열) -> {열 이름: 값}
    return {name: table[:, i] for i, name in enumerate(columns)}


def load_node_log(path):
    # node_log CSV -> {열 이름: 값}
    with open(path) as f:
        columns = f.readline().strip().split(',')
    return node_columns(np.loadtxt(path, delimiter=',', skiprows=1, dtype=np.int64), columns)


def node_summary(c):
    # 노드별 요약값 {이름: (p,s) 배열}
    numP, numS = c['p'].max() + 1, c['s'].max() + 1
    node = c['p'] * numS + c['s']
    numNodes = numP * numS

    def per_node(values, how):
        if how == 'max':
            M = np.zeros(numNodes)
            np.maximum.at(M, node, values)
        else:
            M = np.bincount(node, weights=values, minlength=numNodes)
            if how == 'mean':
                M = M / np.maximum(np.bincount(node, minlength=numNodes), 1)
        return M.reshape(numP, numS)

    qTotal = sum(np.maximum(c[f'q_{d}'], 0) for d in DIRS)        # 노드 큐 합 (기록 시각)
    qmaxNode = np.max([c[f'qmax_{d}'] for d in DIRS], axis=0)    # 노드 링크 중 최대 큐 (구간)
    return {
        '평균 큐': per_node(qTotal, 'mean'),
        '최대 큐(링크)': per_node(qmaxNode, 'max'),
        '주 흐름 보냄': per_node(c['main_sent'], 'sum'),
        '배경 보냄': per_node(c['bg_sent'], 'sum'),
        '주 오버플로': per_node(c['main_overflow'], 'sum'),
        '배경 오버플로': per_node(c['bg_overflow'], 'sum'),
        '중간 기한 초과': per_node(c['main_late_mid'], 'sum'),
        'TTL 만료': per_node(c['main_ttl_expired'], 'sum'),
    }


def busiest_node(summary):
    # 주 흐름 손실(오버플로 + 중간 기한 초과)이 가장 많은 노드, 손실이 없으면 평균 큐가 가장 긴 노드
    loss = summary['주 오버플로'] + summary['중간 기한 초과']
    M = loss if loss.max() > 0 else summary['평균 큐']
    p, s = np.unravel_index(np.argmax(M), M.shape)
    return int(p), int(s)


def print_node_table(summary, tag):
    numP, numS = summary['평균 큐'].shape
    print(f'[{tag}] 노드별 요약')
    print(f'{"노드":>8}' + ''.join(f'{k:>14}' for k in summary))
    for p in range(numP):
        for s in range(numS):
            print(f'{f"({p},{s})":>8}' + ''.join(
                f'{v[p, s]:>14.1f}' if k == '평균 큐' else f'{int(v[p, s]):>14d}' for k, v in summary.items()))


def fig_node_map(summary, tag):
    # 6x6 지도 8장: 가로 p(궤도면), 세로 s(궤도면 안 위성)
    C = viz_colors()
    use_korean_font(C)
    numP, numS = summary['평균 큐'].shape
    fig, axs = plt.subplots(2, 4, figsize=(17, 8), constrained_layout=True, facecolor='w')
    for ax, (name, M) in zip(axs.ravel(), summary.items()):
        im = ax.imshow(M.T, cmap='Blues', origin='upper', vmin=0, vmax=max(M.max(), 1))
        for p in range(numP):
            for s in range(numS):
                txt = f'{M[p, s]:.1f}' if name == '평균 큐' else f'{int(M[p, s])}'
                ax.text(p, s, txt, ha='center', va='center', fontsize=8,
                        color='w' if M[p, s] > M.max() * 0.6 else C.text)
        ax.set_title(name)
        ax.set_xticks(range(numP)); ax.set_xticklabels([f'p={p}' for p in range(numP)], fontsize=8)
        ax.set_yticks(range(numS)); ax.set_yticklabels([f's={s}' for s in range(numS)], fontsize=8)
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle(f'노드별 요약 ({tag})', fontsize=15, color=C.text)
    return fig


def fig_node_time(c, nodeP, nodeS, tag):
    # 노드 1개의 시간 변화: 링크별 최대 큐 / 보낸 수·손실 / 큐 안 주 흐름 패킷의 남은 기한
    C = viz_colors()
    use_korean_font(C)
    sel = (c['p'] == nodeP) & (c['s'] == nodeS)
    t = c['step'][sel] / 1000   # 초
    fig, axs = plt.subplots(3, 1, figsize=(13, 9), sharex=True, constrained_layout=True, facecolor='w')

    ax = axs[0]
    for k, d in enumerate(DIRS):
        q = c[f'qmax_{d}'][sel]
        if (q >= 0).any():   # 링크가 있는 방향만
            ax.plot(t, q, color=C.series[k], linewidth=1, label=f'{DIRS_KO[k]} 링크')
    ax.set_ylabel('링크 큐 최대 길이\n(기록 구간)')
    ax.legend(loc='upper right', ncol=4)

    ax = axs[1]
    ax.plot(t, c['main_sent'][sel], color=C.series[0], linewidth=1, label='주 흐름 보냄')
    ax.plot(t, c['main_overflow'][sel], color=C.series[1], linewidth=1, label='주 오버플로')
    ax.plot(t, c['main_late_mid'][sel], color=C.series[2], linewidth=1, label='중간 기한 초과')
    ax.set_ylabel('패킷 수 (기록 구간)')
    ax.legend(loc='upper right', ncol=3)

    ax = axs[2]
    rem = c['min_rem_deadline'][sel].astype(float)
    rem[rem < 0] = np.nan   # 큐에 주 흐름 패킷이 없던 시각
    ax.plot(t, rem, '.', color=C.series[0], markersize=3)
    ax.axhline(0, linestyle='--', color=C.muted)
    ax.set_ylabel('큐 안 주 흐름 패킷\n남은 기한 최솟값 (step)')
    ax.set_xlabel('시간 (초)')
    for ax in axs:
        ax.grid(True, color=C.grid)
    fig.suptitle(f'노드 ({nodeP},{nodeS}) 시간 변화 ({tag})', fontsize=15, color=C.text)
    return fig


def save_node_plots(c, tag, mapPath, timePath):
    # main_isl에서 호출: 요약 지도 + 가장 손실이 많은 노드의 시간 변화를 PNG로 저장
    summary = node_summary(c)
    p, s = busiest_node(summary)
    for fig, path in [(fig_node_map(summary, tag), mapPath), (fig_node_time(c, p, s, tag), timePath)]:
        fig.savefig(path, dpi=100, facecolor='w')
        plt.close(fig)
    return p, s
