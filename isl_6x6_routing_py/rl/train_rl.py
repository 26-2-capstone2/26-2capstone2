# 강화학습 학습 스크립트 : route_C가 시뮬레이터 안에서 직접 라우팅하며 배움 (온라인 DQN)
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python rl/train_rl.py                  -> config_rl의 trainEpisodes만큼 학습 (학습 시드 = RL.torchSeed)
#   python rl/train_rl.py 6 3000           -> 에피소드 6개, 에피소드 길이 3000 step (짧게 시험할 때)
#   python rl/train_rl.py 270 0 1          -> 학습 시드 1 (신경망 초기값), 에피소드 길이는 config 그대로 (0 = 기본값)
#   학습 시드 3개를 동시에: 터미널 3개에서 마지막 숫자만 0, 1, 2로 바꿔 실행
#
# 에피소드 e: 혼잡 단계 = trainLevels를 돌아가며, 시드 = trainSeedStart + e (핫스팟 시나리오와 난수 둘 다)
# 검증 평가: 학습 시작 전 1번, 그 뒤 evalEvery 에피소드마다 학습을 멈추고 검증 시드(valSeeds)로 ε 0 평가 -> 학습 곡선
# 저장: 홈 폴더 rl_models/routeC_날짜_s학습시드 (같은 날 또 돌리면 _2, _3)
#   model_epN.pt   saveEvery마다 체크포인트, model_final.pt 마지막
#   train_log.csv  에피소드별 기한 내 도착률, 3개 이상 연속 손실, 보상 성분, ε, 학습 손실, 경험 수, 누적 결정 수 (학습 중 값)
#   eval_log.csv   검증 평가 (단계별, 검증 시드 합계): 누적 결정 수, 도착률, 1분당 연속 손실, 연속 손실 길이 95번째 백분위 등
#   run_info.txt   학습 조건
# 학습 곡선 목표 판정: python analysis/learning_targets.py 학습폴더 [학습폴더 ...]
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_6x6_routing_py를 import 경로에 추가

import numpy as np

from analysis.burst_summary import burst_rate_stats, burst_summary, loss_run_lengths
from config_isl import apply_bg_level, config_isl
from rl.config_rl import config_rl
from rl.rl_agent import DQNAgent
from rl.rl_collector import Collector
from routing.route_C import STATE as C_STATE, set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim

EVAL_COLS = ['evalIndex', 'episode', 'decisions', 'epsilon', 'level', 'onTimeRate', 'burstCount', 'burstPerMin',
             'burstLenP95', 'maxConsecLoss', 'avgLatency_ms', 'meanLoss', 'seconds']


def make_save_dir(RL, topology='grid'):
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), RL.modelDir))   # 환경 변수로 저장 위치 바꿀 수 있음
    base = f'routeC_{datetime.now():%Y-%m-%d}_s{RL.torchSeed}'
    if topology != 'grid':   # 실제 위성군이나 크기를 바꾼 격자는 구조 이름도 붙임 (예: routeC_iridium_2026-11-01_s0)
        base = f"routeC_{topology.replace(':', '')}_{datetime.now():%Y-%m-%d}_s{RL.torchSeed}"
    i = 1
    while True:
        d = os.path.join(root, base if i == 1 else f'{base}_{i}')
        if not os.path.exists(d):
            os.makedirs(d)
            return d
        i += 1


def validate(agent, RL, P, collector):
    # 검증 평가: 단계마다 검증 시드 에피소드를 ε 0, 학습 없이 돌려 합친 지표 (학습은 잠시 멈춤)
    set_agent(agent, RL, explore=False, collector=None)
    rows = []
    for level in RL.valLevels:
        apply_bg_level(P, level)
        G = build_grid(P)
        status, runs, latency = [], [], []
        for seed in RL.valSeeds:
            sample_hotspots(P, G, seed)
            R = run_isl_sim(P, P.genRate, 0, seed, False)
            status.append(R.status)
            runs.append(loss_run_lengths(R.status))                     # 에피소드마다 끊어서 셈
            ok = R.status == 1
            latency.append(R.endTime[ok] - R.genTime[ok])
        status, runs, latency = np.concatenate(status), np.concatenate(runs), np.concatenate(latency)
        minutes = len(RL.valSeeds) * P.simTime * P.stepTime / 60
        rate = burst_rate_stats(runs, P.burstMinLen, minutes)
        bursts = runs[runs >= P.burstMinLen]
        rows.append(dict(level=level,
                         onTimeRate=round(float((status == 1).mean()) * 100, 2),
                         burstCount=int(len(bursts)),
                         burstPerMin=round(rate.burstPerMin, 3),
                         burstLenP95=round(rate.burstLenP95, 1),
                         maxConsecLoss=int(runs.max()) if len(runs) else 0,
                         avgLatency_ms=round(float(latency.mean()) * P.stepTime * 1000, 2) if len(latency) else ''))
    set_agent(agent, RL, explore=True, collector=collector)
    return rows


def train(numEpisodes=None, simTime=None, torchSeed=None):
    P = config_isl()
    P.routeName = 'routeC'
    P.nodeLogEnable = False
    if simTime:
        P.simTime = simTime
    RL = config_rl(P)
    if torchSeed is not None:
        RL.torchSeed = torchSeed
    numEpisodes = numEpisodes or RL.trainEpisodes

    agent = DQNAgent(RL)
    collector = Collector(agent, P, RL, learn=True)
    set_agent(agent, RL, explore=True, collector=collector)
    saveDir = make_save_dir(RL, P.topology)

    with open(os.path.join(saveDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'route_C 온라인 DQN 학습 ({datetime.now():%Y-%m-%d %H:%M})\n')
        f.write(f'에피소드 {numEpisodes}개 x {P.simTime} step, 혼잡 단계 {RL.trainLevels} 돌아가며, 시드 {RL.trainSeedStart}부터, '
                f'학습 시드(신경망 초기값) {RL.torchSeed}\n')
        f.write(f'검증 평가: {RL.evalEvery} 에피소드마다, 검증 시드 {RL.valSeeds}, 단계 {RL.valLevels}, ε 0\n')
        f.write(f'망 구조 {P.topology} ({P.numPlanes} x {P.satsPerPlane}), 출발 {P.srcSat.tolist()} -> 도착 {P.dstSat.tolist()}\n')
        f.write(f'기한 {P.deadline}, TTL {P.ttlInit}, 큐 {P.queueMax}, 링크 용량 {P.linkCapacity}, 초당 {P.genRate}개, '
                f'배경 트래픽 {getattr(P, "bgMode", "hotspot")}\n')
        f.write('강화학습 설정: ' + ', '.join(f'{k}={v}' for k, v in vars(RL).items()) + '\n')

    logPath = os.path.join(saveDir, 'train_log.csv')
    cols = ['episode', 'level', 'seed', 'onTimeRate', 'lossRate', 'burstCount', 'burstPackets',
            'burstPacketRate', 'maxConsecLoss', 'epsilon', 'decisions', 'burstPenalties',
            'rewardHopSum', 'rewardOutcomeSum', 'rewardBurstSum', 'infeasibleMasks',
            'meanLoss', 'transitions', 'unfinished', 'bufferSize', 'seconds']
    with open(logPath, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(cols)
    evalPath = os.path.join(saveDir, 'eval_log.csv')
    with open(evalPath, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(EVAL_COLS)

    recentLoss = []   # 직전 검증 이후 에피소드들의 학습 손실 (검증 기록용)

    def run_validation(evalIndex, episode):
        t0 = time.time()
        rows = validate(agent, RL, P, collector)
        sec = round(time.time() - t0, 1)
        meanLoss = round(float(np.mean(recentLoss)), 5) if recentLoss else ''
        with open(evalPath, 'a', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            for r in rows:
                r.update(evalIndex=evalIndex, episode=episode, decisions=agent.numDecisions,
                         epsilon=round(agent.epsilon(), 3), meanLoss=meanLoss, seconds=sec)
                w.writerow([r[c] for c in EVAL_COLS])
        recentLoss.clear()
        print('  [검증 %d] 결정 %d번  ' % (evalIndex, agent.numDecisions) +
              '  '.join(f"{r['level']} {r['onTimeRate']:.2f}% 연속손실 {r['burstPerMin']:.2f}/분" for r in rows) + f'  ({sec}초)')

    print(f'저장 폴더: {saveDir}')
    run_validation(0, 0)   # 학습 전 성능 (T50, T90 계산의 시작점)
    for ep in range(numEpisodes):
        level = RL.trainLevels[ep % len(RL.trainLevels)]
        seed = RL.trainSeedStart + ep
        apply_bg_level(P, level)
        G = build_grid(P)
        sample_hotspots(P, G, seed)
        collector.reset_stats()
        maskFallbackStart = C_STATE.infeasibleMasks

        t0 = time.time()
        R = run_isl_sim(P, P.genRate, 0, seed, False)   # 시뮬레이터 ε는 0 (탐험은 에이전트)
        unfinished = collector.finish()
        burst = burst_summary(R.status, P.burstMinLen)
        if RL.burstEnabled and collector.numBurstPenalties != burst.burstPackets:   # 연속 손실 패킷마다 한 번씩 받아야 함
            raise RuntimeError(f'연속 손실 보상 누락: 실제 {collector.numBurstPenalties}, 예상 {burst.burstPackets}')

        row = dict(episode=ep + 1, level=level, seed=seed,
                   onTimeRate=round(float((R.status == 1).mean()) * 100, 2),
                   lossRate=round(float((R.status != 1).mean()) * 100, 2),
                   burstCount=burst.burstCount, burstPackets=burst.burstPackets,
                   burstPacketRate=round(burst.burstPacketRate * 100, 2),
                   maxConsecLoss=burst.maxConsecLoss,
                   epsilon=round(agent.epsilon(), 3),
                   decisions=agent.numDecisions,
                   burstPenalties=collector.numBurstPenalties,
                   rewardHopSum=round(collector.rewardHopSum, 3),
                   rewardOutcomeSum=round(collector.rewardOutcomeSum, 3),
                   rewardBurstSum=round(collector.rewardBurstSum, 3),
                   infeasibleMasks=C_STATE.infeasibleMasks - maskFallbackStart,
                   meanLoss=round(float(np.mean(collector.losses)), 5) if collector.losses else '',
                   transitions=collector.numTransitions, unfinished=unfinished,
                   bufferSize=len(agent.buffer), seconds=round(time.time() - t0, 1))
        if collector.losses:
            recentLoss.append(float(np.mean(collector.losses)))
        with open(logPath, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([row[c] for c in cols])
        print(f"[{ep + 1}/{numEpisodes}] {level:6s} 도착률 {row['onTimeRate']:6.2f}%  최대 연속 손실 {row['maxConsecLoss']:4d}  "
              f"ε {row['epsilon']:.3f}  학습 손실 {row['meanLoss']}  ({row['seconds']}초)")

        if (ep + 1) % RL.saveEvery == 0:
            agent.save(os.path.join(saveDir, f'model_ep{ep + 1}.pt'))
        if (ep + 1) % RL.evalEvery == 0 or ep + 1 == numEpisodes:
            run_validation((ep + 1 + RL.evalEvery - 1) // RL.evalEvery, ep + 1)

    agent.save(os.path.join(saveDir, 'model_final.pt'))
    print(f'학습 끝: {os.path.join(saveDir, "model_final.pt")}')
    return saveDir


if __name__ == '__main__':
    args = sys.argv[1:]
    train(int(args[0]) if len(args) > 0 else None,
          (int(args[1]) or None) if len(args) > 1 else None,
          int(args[2]) if len(args) > 2 else None)
