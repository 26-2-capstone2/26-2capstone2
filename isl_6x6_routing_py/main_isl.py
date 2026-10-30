# 메인 실행 파일 - 전체 시뮬레이션을 돌리고 결과(CSV, GIF, PNG)를 results 폴더에 저장

# ISL 2D Grid 라우팅 시뮬레이션 실행 (라우팅은 config_isl.py의 P.routeName)
# 생성률 x ε 2종류 실행
#   ε = 0   : 성능 측정용 -> 지표, 애니메이션
#   ε = 0.1 : 데이터 수집용 -> 강화학습용 결정 기록 / 패킷 기록 CSV
import csv
import glob
import os
import random
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use('Agg')   # 그림은 파일로만 저장 (창은 show_results에서 띄움)
import numpy as np

from viz.animate_run import animate_run
from sim.bg_traffic import describe_hotspots, sample_hotspots
from sim.build_grid import build_grid
from analysis.compute_metrics import compute_metrics
from config_isl import apply_bg_level, config_isl
from sim.episodes import merge_episodes, total_params
from sim.node_log import NODE_LOG_COLUMNS
from viz.plot_analysis import plot_analysis
from viz.plot_metrics import plot_metrics
from viz.plot_nodes import node_columns, save_node_plots
from sim.run_isl_sim import run_isl_sim
from analysis.save_results import save_results

P = config_isl()
baseDir = os.path.dirname(os.path.abspath(__file__))
outDir = os.environ.get('ISL_RESULTS_DIR', os.path.join(baseDir, 'results'))   # 여러 개를 동시에 돌릴 때는 run_batch.py가 실행마다 따로 지정
os.makedirs(outDir, exist_ok=True)
for old in glob.glob(os.path.join(outDir, '*')):   # 이전 실행 결과 비우기 (파일 이름에 조건이 들어가서 안 지우면 섞임)
    if os.path.isfile(old):
        os.remove(old)

# 배경 트래픽 시나리오: 에피소드마다 시드를 하나씩 써서 핫스팟 위치를 새로 뽑음 (에피소드 e의 시드 = 시작 시드 + e)
#   시작 시드 우선순위: 실행 인자 (python main_isl.py 7) > config의 bgScenarioSeed > (None이면) 무작위
#   같은 시작 시드면 모든 에피소드의 시나리오가 똑같이 재현됨. 무작위로 정했다면 아래에 출력/저장되니 그 값을 다시 넣으면 됨
# 실행 인자 (모두 생략 가능, 순서대로): 시작 시드, 혼잡 단계, 라우팅, (C_RL일 때) 모델 경로
#   예) python main_isl.py 1001 high D_LA_Dijkstra
#   예) python main_isl.py 1 severe C_RL C:/Users/eun/rl_models/C_RL_2026-10-30/model_final.pt
G = build_grid(P)
numEp = int(P.numEpisodes)
if len(sys.argv) > 1:
    P.bgScenarioSeed = int(sys.argv[1])
elif P.bgScenarioSeed is None:
    P.bgScenarioSeed = random.randrange(100000)
if len(sys.argv) > 2:
    apply_bg_level(P, sys.argv[2])
if len(sys.argv) > 3:
    P.routeName = sys.argv[3]
modelPath = None
if P.routeName == 'C_RL':   # 강화학습: 학습된 신경망을 불러와 C_RL에 붙임 (탐험, 학습 없이 Q값이 가장 큰 방향만)
    if len(sys.argv) < 5:
        sys.exit('C_RL은 모델 경로가 필요함: python main_isl.py 시작시드 혼잡단계 C_RL 모델경로')
    from rl.config_rl import config_rl
    from rl.rl_agent import DQNAgent
    from routing.C_RL import set_agent
    modelPath = sys.argv[4]
    RL = config_rl(P)
    agent = DQNAgent(RL)
    agent.load(modelPath)
    set_agent(agent, RL, explore=False)
runName = f'{P.routeName}_{P.bgLevel}'   # 결과 파일과 저장 폴더 이름 (라우팅_혼잡단계, 시작 시드는 run_info.txt에 기록)
seeds = [P.bgScenarioSeed + e for e in range(numEp)]
print(f'[실행] {runName} (혼잡 {P.bgLevel}, 시작 시드 {P.bgScenarioSeed}, 기한 {P.deadline})')
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
        tag = f'{runName}_eps{epsilon:.1f}'

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

# 실행 조건 기록 (나중에 학습 데이터가 어떤 조건이었는지 확인용)
with open(os.path.join(outDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
    info = [f'실행 이름: {runName}', f'실행 날짜: {datetime.now():%Y-%m-%d %H:%M}',
            f'라우팅: {P.routeName}' + (f' (모델: {modelPath})' if modelPath else ''), f'혼잡 단계: {P.bgLevel}',
            f'배경 시드: {seeds[0]} ~ {seeds[-1]} (에피소드 {numEp}개 x {P.simTime * P.stepTime:.0f}초)',
            f'핫스팟 개수: {P.bgNumMin} ~ {P.bgNumMax}, 세기: {P.bgLoadMin} ~ {P.bgLoadMax}배, ON/OFF 평균: {P.bgOnMean} / {P.bgOffMean} step',
            f'기한: {P.deadline} step, TTL: {P.ttlInit}, 큐: {P.queueMax}, 링크 용량: {P.linkCapacity}',
            f'생성률: {P.genRate}개/초, epsilon: {P.epsilonList}, ε 시드: {P.randomSeed} ~ {P.randomSeed + numEp - 1}']
    f.write('\n'.join(info) + '\n')

# 결과 자동 저장 (코드 .py + 이미지 + CSV + run_info) - 폴더 이름: 라우팅_혼잡단계_날짜
#   같은 날 같은 이름이 있으면: 시작 시드도 같으면 덮어쓰고 (결과가 같음), 다르면 _2, _3을 붙여 따로 저장
# 저장 경로: 프로젝트(git) 밖의 사용자 홈 폴더 아래 isl_saved_runs (Windows/Mac 모두 동작)
#   다른 곳에 저장하고 싶으면 환경변수 ISL_SAVE_ROOT에 경로를 지정
saveRoot = os.environ.get('ISL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), 'isl_saved_runs'))
seedLine = f'배경 시드: {seeds[0]} ~ {seeds[-1]}'
baseName = f'{runName}_{datetime.now():%Y-%m-%d}'
for i in range(1, 1000):
    saveDir = os.path.join(saveRoot, baseName if i == 1 else f'{baseName}_{i}')
    infoPath = os.path.join(saveDir, 'results', 'run_info.txt')
    if not os.path.exists(saveDir):
        break
    if os.path.exists(infoPath) and seedLine in open(infoPath, encoding='utf-8').read():
        break   # 같은 조건, 같은 시드 -> 덮어씀
save_results(baseDir, outDir, saveDir)
