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
from config_isl import config_isl
from plot_analysis import plot_analysis
from plot_metrics import plot_metrics
from run_isl_sim import run_isl_sim
from save_results import save_results

P = config_isl()
baseDir = os.path.dirname(os.path.abspath(__file__))
outDir = os.path.join(baseDir, 'results')
os.makedirs(outDir, exist_ok=True)

logColumns = ['step', 'packet_id', 'hop', 'cur_p', 'cur_s',
              'q_up', 'q_down', 'q_left', 'q_right',
              'L_up', 'L_down', 'L_left', 'L_right',
              'N_up', 'N_down', 'N_left', 'N_right',
              'rem_dp', 'rem_ds', 'rem_deadline', 'ttl',
              'action', 'choice_type', 'enqueued']
# action: 1 상, 2 하, 3 좌, 4 우 / choice_type: 1 주, 2 대체, 3 우회, 4 무작위
pktColumns = ['packet_id', 'gen_step', 'end_step', 'result', 'hops']
# result: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료


def writetable(rows, columns, path, fmt):
    np.savetxt(path, rows, delimiter=',', header=','.join(columns), comments='', fmt=fmt)


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

        writetable(np.column_stack([np.arange(R.numPackets), R.genTime, R.endTime, R.status, R.hops]),
                   pktColumns, os.path.join(outDir, f'packet_log_{tag}.csv'), '%d')
        if epsilon > 0:
            writetable(R.decisionLog, logColumns, os.path.join(outDir, f'decision_log_{tag}.csv'), '%.15g')
        else:
            animate_run(R, P, os.path.join(outDir, f'anim_{tag}.gif'))

        print(f'[{tag}] steps={R.endStep} gen={R.numPackets} onTime={M.onTimeRate:.3f} loss={M.lossRate:.3f} '
              f'lat={M.avgLatency_ms:.1f}ms hops={M.avgHops:.2f} decisions={R.decisionLog.shape[0]} '
              f'({time.time() - tic:.1f}s)')

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

# 결과 자동 저장 (코드 .py + 이미지 + CSV) - 실행할 때마다 날짜_시분 폴더를 새로 만듦
saveRoot = r'C:\Users\eun\Desktop\capstone_isl\baseline_py'   # 저장 경로
saveDir = os.path.join(saveRoot, datetime.now().strftime('%Y-%m-%d_%H%M'))
save_results(baseDir, outDir, saveDir)
