# 메인 실행 파일 - 전체 시뮬레이션을 돌리고 결과(CSV, GIF, PNG)를 results 폴더에 저장

# ISL 2D Grid B 라우팅 시뮬레이션 실행
# 생성률 x ε 2종류 실행
#   ε = 0   : 성능 측정용 -> 지표, 애니메이션
#   ε = 0.1 : 데이터 수집용 -> 강화학습용 결정 기록 / 패킷 기록 CSV
import csv
import os
import time
from datetime import datetime

import matplotlib
matplotlib.use('Agg')   # 그림은 파일로만 저장 (창은 show_results에서 띄움)
import numpy as np

from animate_run import animate_run
from compute_metrics import compute_metrics
from config_bg import config_bg
from config_isl import config_isl
from node_log import NODE_LOG_COLUMNS
from plot_analysis import plot_analysis
from plot_metrics import plot_metrics
from plot_nodes import node_columns, save_node_plots
from run_isl_sim import DECISION_LOG_COLUMNS, PACKET_LOG_COLUMNS, packet_log_table, run_isl_sim, writetable
from save_results import run_dir, save_results

P = config_isl()   # 배경 부하 단계·시드는 config_bg.py의 mainLevel, mainSeed
print(f'배경 트래픽: {P.bgLevel} (흐름별 {P.bgOnRate[0]}개/step), 배경 시드 {P.bgSeed}')
baseDir = os.path.dirname(os.path.abspath(__file__))
outDir = os.path.join(baseDir, 'results')
os.makedirs(outDir, exist_ok=True)

results = []
runs = []   # 실행 분석 그래프용 (실행 결과 전체)
for epsilon in P.epsilonList:
    for genRate in np.atleast_1d(P.genRate):
        tic = time.time()
        R = run_isl_sim(P, int(genRate), epsilon, P.randomSeed, epsilon == 0)
        M = compute_metrics(R, P)
        results.append(M)
        runs.append(R)
        tag = f'rate{int(genRate)}pps_eps{epsilon:.1f}'

        writetable(packet_log_table(R), PACKET_LOG_COLUMNS, os.path.join(outDir, f'packet_log_{tag}.csv'), '%d')
        if R.nodeLog is not None:
            writetable(R.nodeLog, NODE_LOG_COLUMNS, os.path.join(outDir, f'node_log_{tag}.csv'), '%d')
            save_node_plots(node_columns(R.nodeLog, NODE_LOG_COLUMNS), tag,   # 노드 요약 지도 + 손실 많은 노드 시간 변화
                            os.path.join(outDir, f'node_map_{tag}.png'), os.path.join(outDir, f'node_time_{tag}.png'))
        if epsilon > 0:
            writetable(R.decisionLog, DECISION_LOG_COLUMNS, os.path.join(outDir, f'decision_log_{tag}.csv'), '%.15g')
        else:
            animate_run(R, P, os.path.join(outDir, f'anim_{tag}.gif'))

        print(f'[{tag}] steps={R.endStep} gen={R.numPackets} onTime={M.onTimeRate:.3f} loss={M.lossRate:.3f} '
              f'lat={M.avgLatency_ms:.1f}ms hops={M.avgHops:.2f} decisions={R.decisionLog.shape[0]} '
              f'({time.time() - tic:.1f}s)')
        print(f'    주 흐름 손실: 목적지 기한 초과 {M.lateAtDst}, 중간 기한 초과 {M.lateMid}, '
              f'오버플로 {M.overflow}, TTL 만료 {M.ttlExpired}')
        if P.bgEnable:
            print(f'    배경: 생성 {M.bgGenerated}, 도착 {M.bgDelivered}, 오버플로 {M.bgOverflow}, '
                  f'TTL 만료 {M.bgTtlExpired}, 풀 부족 {M.bgPoolFull}')

# 결과 표 (열 이름 -> 값 목록)
columns = list(vars(results[0]).keys())
T = {c: np.array([getattr(M, c) for M in results]) for c in columns}
with open(os.path.join(outDir, 'metrics_summary.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(columns)
    for M in results:
        w.writerow([getattr(M, c) for c in columns])
plot_metrics(T, P, os.path.join(outDir, 'metrics_summary.png'))    # 지표 비교
plot_analysis(runs, P, os.path.join(outDir, 'run_analysis.png'))   # 실행 분석
for M in results:
    print(vars(M))

# 결과 자동 저장 (코드 .py + 이미지 + CSV)
# 저장 위치: baseline_py\라우팅알고리즘명\(baseline / train / evaluation)\라우팅알고리즘_부하단계_시드
#   예) baseline_py\routeB\baseline\routeB_high_1001  (최상위 경로는 save_results.py의 SAVE_ROOT)
saveDir = run_dir(P.routeName, P.bgLevel, P.bgSeed, config_bg())
with open(os.path.join(outDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
    f.write(f'실행 시각: {datetime.now():%Y-%m-%d %H:%M}\n라우팅: {P.routeName}\n'
            f'배경 부하: {P.bgLevel} (흐름별 {P.bgOnRate[0]} packets/step)\n배경 시드: {P.bgSeed}\n')
save_results(baseDir, outDir, saveDir)
