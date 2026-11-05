# 라우팅 비교 평가 - 평가 시드(1~20)로 A, B, C를 같은 조건에서 돌려 표로 비교
#
# 실행 (isl_routing 폴더에서):
#   python eval_routes.py 모델경로                     -> 혼잡 3단계 x A, B, C, 에피소드 20개
#   python eval_routes.py 모델경로 severe              -> severe만
#   python eval_routes.py 모델경로 all routeA,routeC  -> 고른 라우팅만
#   python eval_routes.py none all routeA,routeB  -> C 없이 (모델 없음)
#   python eval_routes.py 모델경로 all routeA,routeB,routeC 10  -> 에피소드 10개만 (평가 시드 1~10, 빠르게 볼 때)
#   python eval_routes.py 모델1,모델2,모델3                -> 학습 시드별 C 모델 여러 개를 한 번에 (C는 모델마다 따로, A, B는 한 번)
#
# 조건: main_isl.py와 같음 (에피소드 e: 핫스팟 시드 bgScenarioSeed + e, 난수 시드 randomSeed + e, ε 0)
#       C는 탐험 없이 Q값이 가장 큰 방향만 고름, 학습도 안 함
# 저장: 홈 폴더 isl_saved_runs/eval_날짜/ (같은 날 또 돌리면 _2, _3)
#   summary.csv   단계 x 라우팅(x C 모델)별 합계 (1분당 연속 손실, 연속 손실 길이 95번째 백분위 포함)
#   per_seed.csv  평가 시드(에피소드)별 결과 -> 짝지은 승률, 최악 에피소드 비교용
#   run_info.txt
# 최종 성능 목표 판정: python analysis/compare_runs.py 평가폴더
import csv
import os
import sys
from datetime import datetime

import numpy as np

from analysis.burst_summary import burst_rate_stats, loss_run_lengths
from analysis.compute_metrics import compute_metrics
from config_isl import BG_LEVELS, EVENT_LEVELS, apply_bg_level, config_isl
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.episodes import merge_episodes, total_params
from sim.run_isl_sim import run_isl_sim

ALL_ROUTES = ['routeA', 'routeB', 'routeC']


def loss_runs(Rs):
    # 에피소드별 연속 손실 구간 길이 (에피소드 경계에서 끊음)
    return np.concatenate([loss_run_lengths(r.status) for r in Rs])


def evaluate(level, route, modelPath=None, numEpisodes=None, cRun=''):
    # 반환: 합계 한 줄, 평가 시드(에피소드)별 줄 목록
    P = config_isl()
    if numEpisodes:
        P.numEpisodes = numEpisodes
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
    minutes = P.numEpisodes * P.simTime * P.stepTime / 60
    rate = burst_rate_stats(runs, P.burstMinLen, minutes)
    perSeed = []
    for e, r in enumerate(Rs):
        er = loss_run_lengths(r.status)
        ok = r.status == 1
        arr = (r.status == 1) | (r.status == 2)          # 평균 지연은 compute_metrics와 같게 목적지 도착 패킷 전체
        eRate = burst_rate_stats(er, P.burstMinLen, P.simTime * P.stepTime / 60)
        perSeed.append(dict(level=level, route=route, cRun=cRun, seed=P.randomSeed + e,
                            onTimeRate=round(float(ok.mean()) * 100, 2),
                            burstCount=int((er >= P.burstMinLen).sum()),
                            burstPerMin=round(eRate.burstPerMin, 3),
                            burstLenP95=round(eRate.burstLenP95, 1),
                            maxConsecLoss=int(er.max()) if len(er) else 0,
                            avgLatency_ms=round(float((r.endTime[arr] - r.genTime[arr]).mean()) * P.stepTime * 1000, 2)
                            if arr.any() else ''))
    return dict(level=level, route=route, cRun=cRun,
                onTimeRate=round(M.onTimeRate * 100, 2), lossRate=round(M.lossRate * 100, 2),
                 burstMinLen=M.burstMinLen, burstCount=M.burstCount,
                 burstPackets=M.burstLossPackets, burstPacketRate=round(M.burstLossRate * 100, 2),
                 burstShareOfLoss=round(M.burstShareOfLoss * 100, 1), avgBurstLen=round(M.avgBurstLen, 2),
                 maxConsecLoss=M.maxConsecLoss, lossRuns=len(runs),
                 infeasibleMasks=C_STATE.infeasibleMasks if C_STATE is not None else 0,
                runs_ge5=int((runs >= 5).sum()), runs_ge10=int((runs >= 10).sum()),
                avgLatency_ms=round(M.avgLatency_ms, 2),
                worstEpisodeOnTime=round(min(float((r.status == 1).mean()) for r in Rs) * 100, 1),
                burstPerMin=round(rate.burstPerMin, 3), burstLenP95=round(rate.burstLenP95, 1)), perSeed


def main():
    args = sys.argv[1:]
    models = args[0].split(',') if args and args[0] != 'none' else []   # C 모델 여러 개 (학습 시드별)
    levels = list(BG_LEVELS) if len(args) < 2 or args[1] == 'all' else [args[1]]
    routes = args[2].split(',') if len(args) > 2 else ALL_ROUTES
    numEpisodes = int(args[3]) if len(args) > 3 else None   # 없으면 config의 numEpisodes (20)
    if 'routeC' in routes and not models:
        routes.remove('routeC')
        print('모델 경로가 없어서 route_C는 빼고 평가')

    root = os.environ.get('ISL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), 'isl_saved_runs'))   # main_isl.py와 같은 환경 변수
    topo = config_isl().topology
    base = f'eval_{datetime.now():%Y-%m-%d}' if topo == 'grid' else f"eval_{topo.replace(':', '')}_{datetime.now():%Y-%m-%d}"
    i = 1
    while os.path.exists(os.path.join(root, base if i == 1 else f'{base}_{i}')):
        i += 1
    saveDir = os.path.join(root, base if i == 1 else f'{base}_{i}')
    os.makedirs(saveDir)

    rows, seedRows = [], []
    for level in levels:
        for route in routes:
            for k, model in enumerate(models if route == 'routeC' else [None]):
                row, perSeed = evaluate(level, route, model, numEpisodes, k if route == 'routeC' else '')
                rows.append(row)
                seedRows += perSeed
                name = route + (f' #{k}' if route == 'routeC' and len(models) > 1 else '')
                print(f"{level:6s} {name:14s} 도착률 {row['onTimeRate']:6.2f}%  손실률 {row['lossRate']:5.2f}%  "
                      f"연속 손실 {row['burstPerMin']:.2f}/분  최대 연속 손실 {row['maxConsecLoss']:4d}  평균 지연 {row['avgLatency_ms']} ms")

    with open(os.path.join(saveDir, 'summary.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(saveDir, 'per_seed.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(seedRows[0]))
        w.writeheader()
        w.writerows(seedRows)
    P = config_isl()
    if numEpisodes:
        P.numEpisodes = numEpisodes
    with open(os.path.join(saveDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'라우팅 비교 평가 ({datetime.now():%Y-%m-%d %H:%M})\n')
        f.write(f'C 모델: {models}\n')
        f.write(f'조건: 기한 {P.deadline}, TTL {P.ttlInit}, 큐 {P.queueMax}, 링크 용량 {P.linkCapacity}, 초당 {P.genRate}개, '
                f'평가 시드 {P.randomSeed}~{P.randomSeed + P.numEpisodes - 1} (에피소드 {P.numEpisodes}개 x {P.simTime} step), ε 0\n')
        table = EVENT_LEVELS if getattr(P, 'bgMode', 'hotspot') == 'event' else BG_LEVELS
        for level in levels:
            f.write(f'혼잡 {level} ({getattr(P, "bgMode", "hotspot")}): {table[level]}\n')
    print(f'저장: {saveDir}')


if __name__ == '__main__':
    main()
