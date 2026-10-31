# 강화학습 학습 스크립트 - C_RL이 시뮬레이터 안에서 직접 라우팅하며 배움 (온라인 DQN)
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python rl/train_rl.py                  -> config_rl의 trainEpisodes만큼 학습
#   python rl/train_rl.py 6 3000           -> 에피소드 6개, 에피소드 길이 3000 step (짧게 시험할 때)
#
# 에피소드 e: 혼잡 단계 = trainLevels를 돌아가며, 시드 = trainSeedStart + e (핫스팟 시나리오와 난수 둘 다)
# 저장: 홈 폴더 rl_models/C_RL_날짜 (같은 날 또 돌리면 _2, _3)
#   model_epN.pt   saveEvery마다 체크포인트, model_final.pt 마지막
#   train_log.csv  에피소드별 기한 내 도착률, 3개 이상 연속 손실, 보상 성분, ε, 학습 손실, 경험 수
#   run_info.txt   학습 조건
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_6x6_routing_py를 import 경로에 추가

import numpy as np

from analysis.compute_metrics import burst_summary
from config_isl import apply_bg_level, config_isl
from rl.config_rl import config_rl
from rl.rl_agent import DQNAgent
from rl.rl_collector import Collector
from routing.C_RL import STATE as C_STATE, set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim


def make_save_dir(RL):
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), RL.modelDir))   # 환경 변수로 저장 위치 바꿀 수 있음
    base = f'C_RL_{datetime.now():%Y-%m-%d}'
    i = 1
    while True:
        d = os.path.join(root, base if i == 1 else f'{base}_{i}')
        if not os.path.exists(d):
            os.makedirs(d)
            return d
        i += 1


def train(numEpisodes=None, simTime=None):
    P = config_isl()
    P.routeName = 'C_RL'
    P.nodeLogEnable = False
    if simTime:
        P.simTime = simTime
    RL = config_rl(P)
    numEpisodes = numEpisodes or RL.trainEpisodes

    agent = DQNAgent(RL)
    collector = Collector(agent, P, RL, learn=True)
    set_agent(agent, RL, explore=True, collector=collector)
    saveDir = make_save_dir(RL)

    with open(os.path.join(saveDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'C_RL 온라인 DQN 학습 ({datetime.now():%Y-%m-%d %H:%M})\n')
        f.write(f'에피소드 {numEpisodes}개 x {P.simTime} step, 혼잡 단계 {RL.trainLevels} 돌아가며, 시드 {RL.trainSeedStart}부터\n')
        f.write(f'기한 {P.deadline}, TTL {P.ttlInit}, 큐 {P.queueMax}, 링크 용량 {P.linkCapacity}, 초당 {P.genRate}개\n')
        f.write('강화학습 설정: ' + ', '.join(f'{k}={v}' for k, v in vars(RL).items()) + '\n')

    logPath = os.path.join(saveDir, 'train_log.csv')
    cols = ['episode', 'level', 'seed', 'onTimeRate', 'lossRate', 'burstCount', 'burstPackets',
            'burstPacketRate', 'maxConsecLoss', 'epsilon', 'burstPenalties',
            'rewardHopSum', 'rewardOutcomeSum', 'rewardBurstSum', 'infeasibleMasks',
            'meanLoss', 'transitions', 'unfinished', 'bufferSize', 'seconds']
    with open(logPath, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(cols)

    print(f'저장 폴더: {saveDir}')
    for ep in range(numEpisodes):
        level = RL.trainLevels[ep % len(RL.trainLevels)]
        seed = RL.trainSeedStart + ep
        apply_bg_level(P, level)
        G = build_grid(P)
        sample_hotspots(P, G, seed)
        collector.reset_stats()
        maskFallbackStart = C_STATE.infeasibleMasks

        t0 = time.time()
        R = run_isl_sim(P, P.genRate, 0, seed, False)   # 시뮬레이터 ε는 0 (탐험은 에이전트가 함)
        unfinished = collector.finish()
        burst = burst_summary(R.status, P.burstMinLen)
        expectedPenalties = int(sum(max(0, length - P.burstMinLen + 1) for length in burst.lossRuns))
        if RL.consecPenalty > 0 and collector.numBurstPenalties != expectedPenalties:
            raise RuntimeError(f'연속 손실 보상 누락: 실제 {collector.numBurstPenalties}, 예상 {expectedPenalties}')

        row = dict(episode=ep + 1, level=level, seed=seed,
                   onTimeRate=round(float((R.status == 1).mean()) * 100, 2),
                   lossRate=round(float((R.status != 1).mean()) * 100, 2),
                   burstCount=burst.burstCount, burstPackets=burst.burstPackets,
                   burstPacketRate=round(burst.burstPacketRate * 100, 2),
                   maxConsecLoss=burst.maxConsecLoss,
                   epsilon=round(agent.epsilon(), 3),
                   burstPenalties=collector.numBurstPenalties,
                   rewardHopSum=round(collector.rewardHopSum, 3),
                   rewardOutcomeSum=round(collector.rewardOutcomeSum, 3),
                   rewardBurstSum=round(collector.rewardBurstSum, 3),
                   infeasibleMasks=C_STATE.infeasibleMasks - maskFallbackStart,
                   meanLoss=round(float(np.mean(collector.losses)), 5) if collector.losses else '',
                   transitions=collector.numTransitions, unfinished=unfinished,
                   bufferSize=len(agent.buffer), seconds=round(time.time() - t0, 1))
        with open(logPath, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([row[c] for c in cols])
        print(f"[{ep + 1}/{numEpisodes}] {level:6s} 도착률 {row['onTimeRate']:6.2f}%  최대 연속 손실 {row['maxConsecLoss']:4d}  "
              f"ε {row['epsilon']:.3f}  학습 손실 {row['meanLoss']}  ({row['seconds']}초)")

        if (ep + 1) % RL.saveEvery == 0:
            agent.save(os.path.join(saveDir, f'model_ep{ep + 1}.pt'))

    agent.save(os.path.join(saveDir, 'model_final.pt'))
    print(f'학습 끝: {os.path.join(saveDir, "model_final.pt")}')
    return saveDir


if __name__ == '__main__':
    args = sys.argv[1:]
    train(int(args[0]) if len(args) > 0 else None, int(args[1]) if len(args) > 1 else None)
