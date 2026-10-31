# 라우팅 비교 평가 - 평가 시드(1~20)로 A, B, C, D를 같은 조건에서 돌려 표로 비교
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python eval_routes.py 모델경로                     -> 혼잡 3단계 x A, B, C, D, 에피소드 20개
#   python eval_routes.py 모델경로 severe              -> severe만
#   python eval_routes.py 모델경로 all routeA,routeC  -> 고른 라우팅만
#   python eval_routes.py none all routeA,routeB  -> C 없이 (모델 없음)
#
# 조건: main_isl.py와 같음 (에피소드 e: 핫스팟 시드 bgScenarioSeed + e, 난수 시드 randomSeed + e, ε 0)
#       C는 탐험 없이 Q값이 가장 큰 방향만 고름, 학습도 안 함
# 저장: 홈 폴더 isl_saved_runs/eval_날짜/summary.csv (같은 날 또 돌리면 _2, _3), run_info.txt
import csv
import os
import sys
from datetime import datetime

import numpy as np

from analysis.burst_summary import loss_run_lengths
from analysis.compute_metrics import compute_metrics
from config_isl import BG_LEVELS, apply_bg_level, config_isl
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.episodes import merge_episodes, total_params
from sim.run_isl_sim import run_isl_sim

ALL_ROUTES = ['routeA', 'routeB', 'routeC']


def loss_runs(Rs):
    # 에피소드별 연속 손실 구간 길이 (에피소드 경계에서 끊음)
    return np.concatenate([loss_run_lengths(r.status) for r in Rs])


def evaluate(level, route, modelPath=None):
    P = config_isl()
    apply_bg_level(P, level)
    P.routeName = route
    P.nodeLogEnable = False
    C_STATE = None
    if route == 'routeC':
        from rl.config_rl import config_rl   # PyTorch는 C를 평가할 때만 필요
        from rl.rl_agent import DQNAgent
        from routing.route_C import STATE as C_STATE, set_agent
        RL = config_rl(P)
        agent = DQNAgent(RL)
        agent.load(modelPath)
        set_agent(agent, RL, explore=False)

    G = build_grid(P)
    Rs = []
    for e in range(P.numEpisodes):
        sample_hotspots(P, G, P.bgScenarioSeed + e)
        Rs.append(run_isl_sim(P, P.genRate, 0, P.randomSeed + e, False))
    M = compute_metrics(merge_episodes(Rs, P), total_params(P))
    runs = loss_runs(Rs)
    return dict(level=level, route=route,
                onTimeRate=round(M.onTimeRate * 100, 2), lossRate=round(M.lossRate * 100, 2),
                 burstMinLen=M.burstMinLen, burstCount=M.burstCount,
                 burstPackets=M.burstPackets, burstPacketRate=round(M.burstPacketRate * 100, 2),
                 maxConsecLoss=M.maxConsecLoss, lossRuns=len(runs),
                 infeasibleMasks=C_STATE.infeasibleMasks if C_STATE is not None else 0,
                runs_ge5=int((runs >= 5).sum()), runs_ge10=int((runs >= 10).sum()),
                avgLatency_ms=round(M.avgLatency_ms, 2),
                worstEpisodeOnTime=round(min(float((r.status == 1).mean()) for r in Rs) * 100, 1))


def main():
    args = sys.argv[1:]
    modelPath = args[0] if args and args[0] != 'none' else None
    levels = list(BG_LEVELS) if len(args) < 2 or args[1] == 'all' else [args[1]]
    routes = args[2].split(',') if len(args) > 2 else ALL_ROUTES
    if 'routeC' in routes and not modelPath:
        routes.remove('routeC')
        print('모델 경로가 없어서 route_C는 빼고 평가')

    root = os.environ.get('ISL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), 'isl_saved_runs'))   # main_isl.py와 같은 환경 변수
    base = f'eval_{datetime.now():%Y-%m-%d}'
    i = 1
    while os.path.exists(os.path.join(root, base if i == 1 else f'{base}_{i}')):
        i += 1
    saveDir = os.path.join(root, base if i == 1 else f'{base}_{i}')
    os.makedirs(saveDir)

    rows = []
    for level in levels:
        for route in routes:
            row = evaluate(level, route, modelPath)
            rows.append(row)
            print(f"{level:6s} {route:14s} 도착률 {row['onTimeRate']:6.2f}%  손실률 {row['lossRate']:5.2f}%  "
                  f"최대 연속 손실 {row['maxConsecLoss']:4d}  평균 지연 {row['avgLatency_ms']} ms")

    with open(os.path.join(saveDir, 'summary.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    P = config_isl()
    with open(os.path.join(saveDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'라우팅 비교 평가 ({datetime.now():%Y-%m-%d %H:%M})\n')
        f.write(f'C 모델: {modelPath}\n')
        f.write(f'조건: 기한 {P.deadline}, TTL {P.ttlInit}, 큐 {P.queueMax}, 링크 용량 {P.linkCapacity}, 초당 {P.genRate}개, '
                f'평가 시드 {P.randomSeed}~{P.randomSeed + P.numEpisodes - 1} (에피소드 {P.numEpisodes}개 x {P.simTime} step), ε 0\n')
        for level in levels:
            f.write(f'혼잡 {level}: {BG_LEVELS[level]}\n')
    print(f'저장: {saveDir}')


if __name__ == '__main__':
    main()
