# 적응 스크립트 : 다른 격자로 학습한 C 모델을 새 격자에서 짧게 추가 학습 (학습 -> 적응 -> 평가 중 "적응")
#
# 실행 (isl_routing 폴더에서, 적응할 격자는 환경 변수 ISL_TOPOLOGY로 줌. run.py "C 적응"이 대신 실행해 줌):
#   ISL_TOPOLOGY=grid:24x24 python rl/adapt_rl.py 모델경로                -> 적응 에피소드 RL.adaptEpisodes개 (기본 5)
#   ISL_TOPOLOGY=grid:24x24 python rl/adapt_rl.py 모델경로 10             -> 10개
#   ISL_TOPOLOGY=grid:24x24 python rl/adapt_rl.py 모델경로 5 0:1:2        -> 혼잡 단계 비율 base:high:severe (기본은 학습과 같음)
#
# 시험과 섞이지 않게 하는 규칙
#   적응 시드 RL.adaptSeedStart(2001)부터: 학습(1001~), 검증(501~503), 최종 평가(1~20)와 겹치지 않음
#   적응 뒤 최종 평가는 평가 시드 1~20으로 학습 없이 (run.py "B, C 비교 평가"에서 적응한 모델을 고르면 됨)
# 적응 설정 (rl/config_rl.py): ε 고정 adaptEps (0.05), 학습률 adaptLr (1e-5), 버퍼는 비어서 시작해 adaptLearnStart만큼 쌓이면 학습
#   그 밖의 학습 방식(보상, 타깃 신경망, 학습 주기, 측정 흐름을 장거리 쌍 중 무작위로 뽑기)은 학습과 같음
# 검증: 적응 전(evalIndex 0)과 적응 뒤(evalIndex 1)에 이 격자의 검증 시드(501~503)로 ε 0 평가 -> eval_log.csv (측정 흐름 기준)
# 저장: 홈 폴더 rl_models/routeC_adapt_<원래 모델 폴더>_to_<격자>_날짜 (같은 날 또 하면 _2, _3)
#   model_final.pt (적응한 모델), train_log.csv (적응 에피소드별 기록), eval_log.csv, run_info.txt (원래 모델, 학습 격자, 적응 격자)
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing를 import 경로에 추가

import numpy as np

from config_isl import apply_bg_level, config_isl
from rl.config_rl import config_rl
from rl.model_info import model_grid
from rl.rl_agent import DQNAgent
from rl.rl_collector import Collector
from rl.train_rl import EVAL_COLS, apply_level_ratio, validate
from routing.route_C import set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim


def make_adapt_dir(RL, modelPath, topology):
    root = os.environ.get('RL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), RL.modelDir))
    src = os.path.basename(os.path.dirname(os.path.abspath(modelPath)))
    model = os.path.splitext(os.path.basename(modelPath))[0]
    src = src if model == 'model_final' else f'{src}-{model}'
    base = f"routeC_adapt_{src}_to_{topology.replace(':', '')}_{datetime.now():%Y-%m-%d}"
    i = 1
    while True:
        d = os.path.join(root, base if i == 1 else f'{base}_{i}')
        if not os.path.exists(d):
            os.makedirs(d)
            return d
        i += 1


def adapt(modelPath, numEpisodes=None, levelRatio=None):
    P = config_isl()
    P.routeName = 'routeC'
    P.nodeLogEnable = False
    RL = config_rl(P)
    if levelRatio:
        apply_level_ratio(RL, levelRatio)
    numEpisodes = numEpisodes or RL.adaptEpisodes
    RL.epsStart = RL.epsEnd = RL.adaptEps   # ε 고정
    RL.learnStart = RL.adaptLearnStart

    agent = DQNAgent(RL)
    agent.load(modelPath)
    for g in agent.opt.param_groups:        # 저장된 학습률 대신 적응 학습률
        g['lr'] = RL.adaptLr
    collector = Collector(agent, P, RL, learn=True)
    set_agent(agent, RL, explore=True, collector=collector)
    saveDir = make_adapt_dir(RL, modelPath, P.topologyName)

    with open(os.path.join(saveDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'route_C 적응 ({datetime.now():%Y-%m-%d %H:%M})\n')
        f.write(f'원래 모델: {os.path.abspath(modelPath)}\n')
        f.write(f'원래 학습 격자: {model_grid(modelPath)}\n')
        f.write(f'적응 격자 {P.topologyName} ({P.numPlanes} x {P.satsPerPlane}), 측정 흐름 적응 {RL.flowZeroRandomTrain}, 검증 {P.flowZeroTest} (가장 먼 쌍 {P.srcSat.tolist()} -> {P.dstSat.tolist()})\n')
        f.write(f'적응 에피소드 {numEpisodes}개 x {P.simTime} step, 시드 {RL.adaptSeedStart}부터, 혼잡 단계 {RL.trainLevelWeights}, '
                f'ε {RL.adaptEps} 고정, 학습률 {RL.adaptLr}, 학습 시작 경험 수 {RL.adaptLearnStart}\n')
        f.write(f'검증: 적응 전, 적응 뒤 2번, 검증 시드 {RL.valSeeds}, 단계 {RL.valLevels}, ε 0, 측정 흐름 기준\n')
        f.write(f'기한 {P.deadline}, TTL {P.ttlInit}, 큐 {P.queueMax}, 링크 용량 {P.linkCapacity}, 초당 {P.genRate}개, '
                f'배경 트래픽 {getattr(P, "bgMode", "hotspot")}\n')
        f.write('강화학습 설정: ' + ', '.join(f'{k}={v}' for k, v in vars(RL).items()) + '\n')

    evalPath = os.path.join(saveDir, 'eval_log.csv')
    with open(evalPath, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(EVAL_COLS + ['stage'])

    def run_validation(index, episode, stage):
        t0 = time.time()
        rows = validate(agent, RL, P, collector)
        with open(evalPath, 'a', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            for r in rows:
                r.update(evalIndex=index, episode=episode, decisions=agent.numDecisions, epsilon=RL.adaptEps,
                         meanLoss='', seconds=round(time.time() - t0, 1), stage=stage)
                w.writerow([r[c] for c in EVAL_COLS + ['stage']])
        print(f'  [{stage}] ' + '  '.join(f"{r['level']} 측정 흐름 도착률 {r['onTimeRate']:.2f}%  "
                                          f"최대 연속 손실 {r['maxConsecLoss']}" for r in rows))
        return rows

    logPath = os.path.join(saveDir, 'train_log.csv')
    cols = ['episode', 'level', 'seed', 'onTimeRate', 'measuredOnTimeRate', 'meanLoss', 'transitions', 'bufferSize', 'seconds']
    with open(logPath, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(cols)

    w = np.array([RL.trainLevelWeights[lv] for lv in RL.trainLevels], dtype=float)
    levelSeq = [str(lv) for lv in np.random.RandomState(RL.adaptSeedStart).choice(RL.trainLevels, size=numEpisodes, p=w / w.sum())]
    print(f'저장 폴더: {saveDir}')
    print(f'원래 학습 격자 {model_grid(modelPath)} -> 적응 격자 {P.topologyName}')
    before = run_validation(0, 0, '적응 전')
    for ep in range(numEpisodes):
        level = levelSeq[ep]
        seed = RL.adaptSeedStart + ep
        apply_bg_level(P, level)
        G = build_grid(P)
        P.flowZeroRandom = RL.flowZeroRandomTrain
        sample_hotspots(P, G, seed)
        collector.reset_stats()
        t0 = time.time()
        R = run_isl_sim(P, P.genRate, 0, seed, False)
        collector.finish()
        row = dict(episode=ep + 1, level=level, seed=seed,
                   onTimeRate=round(float((R.status == 1).mean()) * 100, 2),
                   measuredOnTimeRate=round(float((R.status[R.packetFlow == 0] == 1).mean()) * 100, 2),
                   meanLoss=round(float(np.mean(collector.losses)), 5) if collector.losses else '',
                   transitions=collector.numTransitions, bufferSize=len(agent.buffer), seconds=round(time.time() - t0, 1))
        with open(logPath, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([row[c] for c in cols])
        print(f"[적응 {ep + 1}/{numEpisodes}] {level:6s} 측정 흐름 도착률 {row['measuredOnTimeRate']:6.2f}%  "
              f"학습 손실 {row['meanLoss']}  ({row['seconds']}초)")
    after = run_validation(1, numEpisodes, '적응 뒤')
    agent.save(os.path.join(saveDir, 'model_final.pt'))
    print('검증 (측정 흐름 기한 내 도착률): ' + ', '.join(
        f"{b['level']} {b['onTimeRate']:.2f}% -> {a['onTimeRate']:.2f}%" for b, a in zip(before, after)))
    print(f'적응 끝: {os.path.join(saveDir, "model_final.pt")}')
    return saveDir


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        sys.exit('사용법: ISL_TOPOLOGY=grid:24x24 python rl/adapt_rl.py 모델경로 [적응 에피소드 수] [혼잡 단계 비율]')
    adapt(args[0], int(args[1]) if len(args) > 1 else None, args[2] if len(args) > 2 else None)
