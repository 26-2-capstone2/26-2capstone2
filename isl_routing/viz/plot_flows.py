# 흐름별 결과 그림 - 측정 흐름(흐름 0)과 다른 GSL 흐름(1 ~ numFlows-1)을 하나씩 나눠서 봄
#   전체 합계만 보면 흐름 하나가 통째로 끊겨도 "도착률 75%"처럼 괜찮아 보일 수 있어서 흐름별로 나눔
#
# 실행 (isl_routing 폴더에서):
#   python viz/plot_flows.py 결과폴더 [grid 구조]
#   예) python viz/plot_flows.py ~/isl_saved_runs/routeC_base_starlink_2026-11-10/results starlink
#   결과폴더 = main_isl.py가 만든 packet_log_*.csv, run_info.txt가 있는 폴더
#   grid 구조를 안 주면 환경 변수 ISL_TOPOLOGY -> 폴더 이름(iridium, starlink) -> grid 순서로 정함
#   (흐름 1~3의 출발, 도착 위성은 packet_log에 없어서 run_info.txt의 배경 시드로 다시 뽑아 씀, 같은 시드면 같은 흐름)
#   main_isl.py (run.py 1번 시뮬레이션)가 끝나면 자동으로 실행됨
#
# 저장 (packet_log마다): flow_analysis_태그.png, flow_summary_태그.csv
#   그림 1. 흐름별 패킷 결과 비율 (기한 내 도착 / 목적지 기한 초과 / 중간 기한 초과 / 큐 오버플로 / TTL 만료)
#   그림 2. 흐름별 연속 손실 횟수, 최대 연속 손실
#   그림 3. 에피소드 x 흐름 기한 내 도착률 (칸 안: 도착률, 출발 -> 도착 위성)
#   그림 4. 시간에 따른 손실 위치 (점 하나 = 잃은 패킷 하나, 색 = 손실 원인)
#   CSV: 에피소드 x 흐름 한 줄씩 (출발, 도착, 결과별 개수, 연속 손실, 평균 지연)
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing를 import 경로에 추가

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from analysis.burst_loss import loss_runs
from viz.viz_colors import use_korean_font, viz_colors

RESULTS = [(1, '기한 내 도착', '#1baf7a'), (2, '목적지 기한 초과', '#eda100'), (3, '중간 기한 초과', '#eb6834'),
           (4, '큐 오버플로', '#2a78d6'), (5, 'TTL 만료', '#8e5bd6')]


def short_name(f):
    return '측정 흐름' if f == 0 else f'GSL 흐름 {f}'


def fmt_sat(s):
    return f'({s[0]},{s[1]})'


def flow_table(status, flow, episode, gen, end, flowsByEp, seeds, burstMinLen):
    # 에피소드 x 흐름 요약 줄 목록
    rows = []
    for e in np.unique(episode):
        me = episode == e
        for f in np.unique(flow[me]):
            m = me & (flow == f)
            s = status[m]
            runs = loss_runs(s)[1]
            arr = (s == 1) | (s == 2)
            src, dst = flowsByEp[int(e)][int(f)] if flowsByEp and int(e) < len(flowsByEp) else (('?', '?'), ('?', '?'))
            rows.append(dict(
                episode=int(e), seed=seeds[int(e)] if seeds and int(e) < len(seeds) else '', flow=int(f),
                src=fmt_sat(src), dst=fmt_sat(dst), generated=int(m.sum()),
                onTime=int((s == 1).sum()), onTimeRate=round(float((s == 1).mean()) * 100, 2),
                lateAtDst=int((s == 2).sum()), lateMid=int((s == 3).sum()), overflow=int((s == 4).sum()), ttlExpired=int((s == 5).sum()),
                burstCount=int((runs >= burstMinLen).sum()), maxConsecLoss=int(runs.max()) if len(runs) else 0,
                avgLatency_ms=round(float((end[m][arr] - gen[m][arr]).mean()), 2) if arr.any() else ''))
    return rows


def plot_flows(status, flow, episode, gen, end, flowsByEp, seeds, title, outPng, outCsv,
               burstMinLen=3, simTime=10000, stepTime=0.001):
    status, flow, episode = np.asarray(status), np.asarray(flow), np.asarray(episode)
    gen, end = np.asarray(gen), np.asarray(end)
    rows = flow_table(status, flow, episode, gen, end, flowsByEp, seeds, burstMinLen)
    with open(outCsv, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    C = viz_colors()
    use_korean_font(C)
    flows = sorted(np.unique(flow).tolist())
    eps = sorted(np.unique(episode).tolist())
    nF, nE = len(flows), len(eps)
    fixed0 = flowsByEp and all(fe[0] == flowsByEp[0][0] for fe in flowsByEp)   # 흐름 0이 모든 에피소드에서 같은 경로인지
    names = []
    for f in flows:
        if f == 0 and fixed0:
            names.append(f'측정 흐름 (0)\n{fmt_sat(flowsByEp[0][0][0])}→{fmt_sat(flowsByEp[0][0][1])}')
        elif f == 0:
            names.append('측정 흐름 (0)\n(에피소드마다 다름)')
        else:
            names.append(f'다른 GSL 흐름 {f}\n(에피소드마다 다름)')

    topH, botH = 4.5, max(4.0, 0.32 * nE)   # 위 칸, 아래 칸 높이 (인치). 에피소드가 많으면 아래 칸을 늘림
    fig = plt.figure(figsize=(18, topH + botH + 2.2))
    fig.patch.set_facecolor('white')
    gs = fig.add_gridspec(2, 2, height_ratios=[topH, botH], hspace=0.42 * 4.5 / ((topH + botH) / 2), wspace=0.18)

    # 1. 흐름별 패킷 결과 비율 (누적 가로 막대)
    ax = fig.add_subplot(gs[0, 0])
    left = np.zeros(nF)
    for code, label, color in RESULTS:
        frac = np.array([np.mean(status[flow == f] == code) * 100 for f in flows])
        ax.barh(range(nF), frac, left=left, color=color, label=label, height=0.6)
        for i, (l, v) in enumerate(zip(left, frac)):
            if v >= 6:
                ax.text(l + v / 2, i, f'{v:.0f}%', ha='center', va='center', fontsize=9, color='white')
        left += frac
    ax.set_yticks(range(nF))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel('패킷 비율 (%)')
    ax.set_title('흐름별 패킷 결과')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=5, frameon=False, fontsize=8)

    # 2. 흐름별 연속 손실 횟수, 최대 연속 손실
    ax = fig.add_subplot(gs[0, 1])
    cnt = [sum(r['burstCount'] for r in rows if r['flow'] == f) for f in flows]
    mx = [max([r['maxConsecLoss'] for r in rows if r['flow'] == f] or [0]) for f in flows]
    x = np.arange(nF)
    b1 = ax.bar(x - 0.2, cnt, 0.4, color=C.series[0], label=f'연속 손실 횟수 ({burstMinLen}개 이상, 전체 에피소드 합)')
    ax2 = ax.twinx()
    b2 = ax2.bar(x + 0.2, mx, 0.4, color=C.series[1], label='최대 연속 손실 (개)')
    for bars, axis in ((b1, ax), (b2, ax2)):
        for bar in bars:
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{int(bar.get_height())}',
                      ha='center', va='bottom', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel('연속 손실 횟수 (번)')
    ax2.set_ylabel('최대 연속 손실 (개)')
    ax.set_ylim(0, max(cnt + [1]) * 1.2)
    ax2.set_ylim(0, max(mx + [1]) * 1.2)
    ax.set_title('흐름별 연속 손실')
    ax.legend(handles=[b1, b2], loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False, fontsize=8)

    # 3. 에피소드 x 흐름 도착률
    ax = fig.add_subplot(gs[1, 0])
    grid = np.full((nE, nF), np.nan)
    for r in rows:
        grid[eps.index(r['episode']), flows.index(r['flow'])] = r['onTimeRate']
    cmap = LinearSegmentedColormap.from_list('ontime', ['#c0392b', '#f5c242', '#1baf7a'])
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=100, aspect='auto')
    for r in rows:
        i, j = eps.index(r['episode']), flows.index(r['flow'])
        txt = f"{r['onTimeRate']:.0f}%" if r['onTimeRate'] in (0, 100) else f"{r['onTimeRate']:.1f}%"
        ax.text(j, i, f"{txt}  {r['src']}→{r['dst']}", ha='center', va='center', fontsize=7)
    ax.set_xticks(range(nF))
    ax.set_xticklabels([short_name(f) for f in flows])
    ax.set_yticks(range(nE))
    ax.set_yticklabels([f"{e + 1}" + (f" (시드 {seeds[e]})" if seeds and e < len(seeds) else '') for e in eps], fontsize=8)
    ax.set_ylabel('에피소드')
    ax.set_title('에피소드별 흐름 기한 내 도착률 (칸: 도착률, 출발→도착 위성)')

    # 4. 시간에 따른 손실 위치
    ax = fig.add_subplot(gs[1, 1])
    epLen = simTime * stepTime
    # 전체 시간 (초), 에피소드를 이어 붙임. 여러 에피소드를 합친 결과(merge_episodes, packet_log)는 gen_step이 이미 이어진 시간
    t = gen * stepTime if gen.max(initial=0) >= simTime else episode * epLen + gen * stepTime
    for code, label, color in RESULTS[1:]:
        m = status == code
        if m.any():
            ax.scatter(t[m], flow[m] + (code - 3.5) * 0.12, s=4, marker='|', color=color, label=label, rasterized=True)
    for e in eps[1:]:
        ax.axvline(e * epLen, color=C.grid, lw=0.8)
    ax.set_yticks(flows)
    ax.set_yticklabels([short_name(f) for f in flows])
    ax.set_ylim(max(flows) + 0.6, min(flows) - 0.6)
    ax.set_xlim(0, nE * epLen)
    ax.set_xlabel(f'시간 (초, 에피소드 {nE}개를 이어 붙임, 세로선 = 에피소드 경계)')
    ax.set_title('언제 어느 흐름이 손실됐나 (점 = 잃은 패킷)')
    if (status != 1).any():
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.11), ncol=4, frameon=False, fontsize=8, markerscale=5)
    else:
        ax.text(0.5, 0.5, '손실 없음', transform=ax.transAxes, ha='center', va='center', color=C.muted)

    fig.suptitle(title, fontsize=13)
    fig.savefig(outPng, dpi=130, bbox_inches='tight')
    plt.close(fig)
    return outPng, outCsv


def flows_for_seeds(P, G, seeds):
    # 에피소드별 흐름을 시뮬레이터와 같은 함수(sim/flows.make_flows)로 다시 뽑음 (같은 시드면 같은 흐름)
    from sim.flows import make_flows
    return [make_flows(P, G, sd) for sd in seeds]


def guess_topology(folder):
    # 환경 변수 ISL_TOPOLOGY -> 폴더 이름 (예: ..._grid10x10_..., ..._iridium_...) -> grid
    if os.environ.get('ISL_TOPOLOGY'):
        return os.environ['ISL_TOPOLOGY']
    name = os.path.abspath(folder).lower()
    m = re.search(r'(grid|starlink)(\d+x\d+)', name)
    if m:
        return f'{m.group(1)}:{m.group(2)}'
    for base in ('starlink', 'iridium'):
        if base in name:
            return base
    return 'grid'


def main():
    if len(sys.argv) < 2:
        print('사용법: python viz/plot_flows.py 결과폴더 [grid 구조]')
        return
    folder = os.path.expanduser(sys.argv[1])
    os.environ['ISL_TOPOLOGY'] = sys.argv[2] if len(sys.argv) > 2 else guess_topology(folder)
    from config_isl import config_isl
    from sim.build_grid import build_grid
    P = config_isl()
    G = build_grid(P)
    info = open(os.path.join(folder, 'run_info.txt'), encoding='utf-8').read()
    m = re.search(r'배경 시드: (\d+) ~ (\d+)', info)
    seeds = list(range(int(m.group(1)), int(m.group(2)) + 1))
    flowsByEp = flows_for_seeds(P, G, seeds)
    print(f'grid 구조 {os.environ["ISL_TOPOLOGY"]}, 흐름 0: {flowsByEp[0][0]}')
    for path in sorted(glob.glob(os.path.join(folder, 'packet_log_*.csv'))):
        tag = os.path.basename(path)[len('packet_log_'):-4]
        a = np.loadtxt(path, delimiter=',', skiprows=1, dtype=np.int64, ndmin=2)
        col = {c: i for i, c in enumerate(open(path, encoding='utf-8-sig').readline().strip().split(','))}
        out = plot_flows(a[:, col['result']], a[:, col['flow_id']], a[:, col['episode']], a[:, col['gen_step']], a[:, col['end_step']],
                         flowsByEp, seeds, f'흐름별 결과: {tag} (grid 구조 {os.environ["ISL_TOPOLOGY"]})',
                         os.path.join(folder, f'flow_analysis_{tag}.png'), os.path.join(folder, f'flow_summary_{tag}.csv'),
                         P.burstMinLen, P.simTime, P.stepTime)
        print(f'저장: {out[0]}, {os.path.basename(out[1])}')


if __name__ == '__main__':
    main()
