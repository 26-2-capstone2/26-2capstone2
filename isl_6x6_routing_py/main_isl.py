# 메인 실행 파일 - 전체 시뮬레이션을 돌리고 결과(CSV, GIF, PNG)를 results 폴더에 저장

# ISL 2D Grid 라우팅 시뮬레이션 실행 (라우팅은 config_isl.py의 P.routeName)
# 생성률 x ε 2종류 실행
#   ε = 0   : 성능 측정용 -> 지표, 애니메이션
#   ε = 0.1 : 데이터 수집용 -> 강화학습용 결정 기록 / 패킷 기록 CSV
import csv
import os
import random
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use('Agg')   # 그림은 파일로만 저장 (창은 show_results에서 띄움)
import numpy as np

from animate_run import animate_run
from bg_traffic import describe_hotspots, sample_hotspots
from build_grid import build_grid
from compute_metrics import compute_metrics
from config_isl import config_isl
from episodes import merge_episodes, total_params
from node_log import NODE_LOG_COLUMNS
from plot_analysis import plot_analysis
from plot_metrics import plot_metrics
from plot_nodes import node_columns, save_node_plots
from run_isl_sim import run_isl_sim
from save_results import save_results

P = config_isl()
baseDir = os.path.dirname(os.path.abspath(__file__))
outDir = os.path.join(baseDir, 'results')
os.makedirs(outDir, exist_ok=True)

# 배경 트래픽 시나리오: 에피소드마다 시드를 하나씩 써서 핫스팟 위치를 새로 뽑음 (에피소드 e의 시드 = 시작 시드 + e)
#   시작 시드 우선순위: 실행 인자 (python main_isl.py 7) > config의 bgScenarioSeed > (None이면) 무작위
#   같은 시작 시드면 모든 에피소드의 시나리오가 똑같이 재현됨. 무작위로 정했다면 아래에 출력/저장되니 그 값을 다시 넣으면 됨
G = build_grid(P)
numEp = int(P.numEpisodes)
if len(sys.argv) > 1:
    P.bgScenarioSeed = int(sys.argv[1])
elif P.bgScenarioSeed is None:
    P.bgScenarioSeed = random.randrange(100000)
seeds = [P.bgScenarioSeed + e for e in range(numEp)]
print(f'[라우팅] {P.routeName}')
if P.bgEnable:
    print(f'[배경 시나리오] 시작 시드 {P.bgScenarioSeed}, 에피소드 {numEp}개 x {P.simTime * P.stepTime:.0f}초')
    with open(os.path.join(outDir, 'bg_scenario.csv'), 'w', newline='') as f:   # 어떤 시나리오였는지 결과에 같이 저장
        w = csv.writer(f)
        w.writerow(['episode', 'seed', 'p', 's', 'direction', 'load', 'relevant'])
        for e, sd in enumerate(seeds):
            picked, rates = sample_hotspots(P, G, sd)
            print(f'  에피소드 {e:2d} (시드 {sd}): 핫스팟 {len(picked)}개: {describe_hotspots(picked, rates, P)}')
            for c, r in zip(picked, rates):
                w.writerow([e, sd, c[0], c[1], c[2], round(r / P.linkCapacity, 3), int(c[5])])

logColumns = ['step', 'packet_id', 'hop', 'cur_p', 'cur_s',
              'q_up', 'q_down', 'q_left', 'q_right',
              'L_up', 'L_down', 'L_left', 'L_right',
              'N_up', 'N_down', 'N_left', 'N_right',
              'rem_dp', 'rem_ds', 'rem_deadline', 'ttl',
              'action', 'choice_type', 'enqueued']
# action: 1 상, 2 하, 3 좌, 4 우 / choice_type: 1 주, 2 대체, 3 우회, 4 무작위
pktColumns = ['packet_id', 'gen_step', 'end_step', 'result', 'hops', 'episode']
# result: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료


def writetable(rows, columns, path, fmt):
    np.savetxt(path, rows, delimiter=',', header=','.join(columns), comments='', fmt=fmt)


Pt = total_params(P)   # 후처리용: simTime을 전체 길이(에피소드 길이 x 개수)로 바꾼 복사본
results = []
runs = []   # 실행 분석 그래프용 (실행 결과 전체)
for epsilon in P.epsilonList:
    for genRate in np.atleast_1d(P.genRate):
        tic = time.time()
        eps_runs = []
        for e in range(numEp):
            if P.bgEnable:
                sample_hotspots(P, G, seeds[e])   # 같은 시드면 같은 시나리오 -> ε가 달라도 에피소드 e의 환경은 동일
            eps_runs.append(run_isl_sim(P, int(genRate), epsilon, P.randomSeed + e, epsilon == 0 and e == 0))
        R = merge_episodes(eps_runs, P)
        M = compute_metrics(R, Pt)
        results.append(M)
        runs.append(R)
        tag = f'rate{int(genRate)}pps_eps{epsilon:.1f}'

        writetable(np.column_stack([np.arange(R.numPackets), R.genTime, R.endTime, R.status, R.hops, R.packetEpisode]),
                   pktColumns, os.path.join(outDir, f'packet_log_{tag}.csv'), '%d')
        if R.nodeLog is not None:
            writetable(R.nodeLog, NODE_LOG_COLUMNS, os.path.join(outDir, f'node_log_{tag}.csv'), '%d')
            save_node_plots(node_columns(R.nodeLog, NODE_LOG_COLUMNS), tag,   # 노드 요약 지도 + 손실 많은 노드 시간 변화
                            os.path.join(outDir, f'node_map_{tag}.png'), os.path.join(outDir, f'node_time_{tag}.png'))
        if epsilon > 0:
            writetable(R.decisionLog, logColumns, os.path.join(outDir, f'decision_log_{tag}.csv'), '%.15g')
        else:
            animate_run(eps_runs[0], P, os.path.join(outDir, f'anim_{tag}.gif'))   # 애니메이션은 첫 에피소드만

        print(f'[{tag}] episodes={numEp} steps={R.endStep} gen={R.numPackets} onTime={M.onTimeRate:.3f} loss={M.lossRate:.3f} '
              f'lat={M.avgLatency_ms:.1f}ms hops={M.avgHops:.2f} decisions={R.decisionLog.shape[0]} '
              f'({time.time() - tic:.1f}s)')
        print(f'    주 흐름 손실: 목적지 기한 초과 {M.lateAtDst}, 중간 기한 초과 {M.lateMid}, '
              f'오버플로 {M.overflow}, TTL 만료 {M.ttlExpired}')
        if P.bgEnable:
            print(f'    배경: 생성 {M.bgGenerated}, 도착 {M.bgDelivered}, 오버플로 {M.bgOverflow}, '
                  f'TTL 만료 {M.bgTtlExpired}, 자리 부족 {M.bgSrcDrop}')

# 결과 표 (열 이름 -> 값 목록)
columns = list(vars(results[0]).keys())
T = {c: np.array([getattr(M, c) for M in results]) for c in columns}
with open(os.path.join(outDir, 'metrics_summary.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(columns)
    for M in results:
        w.writerow([getattr(M, c) for c in columns])
plot_metrics(T, Pt, os.path.join(outDir, 'metrics_summary.png'))    # 지표 비교
plot_analysis(runs, Pt, os.path.join(outDir, 'run_analysis.png'))   # 실행 분석
for M in results:
    print(vars(M))

# 결과 자동 저장 (코드 .py + 이미지 + CSV) - 실행할 때마다 날짜_시분 폴더를 새로 만듦
# 저장 경로: 프로젝트(git) 밖의 사용자 홈 폴더 아래 isl_saved_runs (Windows/Mac 모두 동작)
#   다른 곳에 저장하고 싶으면 환경변수 ISL_SAVE_ROOT에 경로를 지정
saveRoot = os.environ.get('ISL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), 'isl_saved_runs'))
saveDir = os.path.join(saveRoot, datetime.now().strftime('%Y-%m-%d_%H%M'))
save_results(baseDir, outDir, saveDir)
