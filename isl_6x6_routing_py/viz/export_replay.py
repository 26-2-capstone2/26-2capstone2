# 재생기용 기록 만들기 - 같은 상황(혼잡 단계, 평가 시드)에서 C와 B를 돌려 웹 재생기(viz/replay/replay.html)가 읽을 파일로 저장
#
# 실행 (isl_6x6_routing_py 폴더에서):
#   python viz/export_replay.py 모델경로 [혼잡단계] [저장폴더]
#   예) python viz/export_replay.py C:/Users/eun/rl_models/routeC_2026-10-30/model_final.pt severe
# 저장: 저장폴더/replay_data.js + replay.html (기본: 홈 폴더 isl_saved_runs/replay_날짜) -> replay.html을 브라우저로 열면 됨
#
# 고르는 구간: 평가 에피소드 0~19 중 D의 연속 손실이 가장 긴 에피소드에서, 그 연속 손실이 시작되기 조금 전부터 WINDOW step
# 기록 내용 (구간 안만)
#   queues[step][link]  링크별 큐 길이 (링크 번호는 links 목록 순서)
#   packets             패킷별 생성 시각, 끝 시각, 결과, 홉 목록 [결정 시각, p, s, 방향, (C만) 4방향 Q값]
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_6x6_routing_py를 import 경로에 추가

import numpy as np

import sim.run_isl_sim as S
from config_isl import apply_bg_level, config_isl
from rl.config_rl import config_rl
from rl.rl_agent import DQNAgent
from routing.route_C import STATE, set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid

WINDOW = 1500        # 재생 구간 길이 (step = ms)
LEAD = 300           # 연속 손실 시작보다 이만큼 앞에서 시작
SEARCH_EPISODES = 20  # 구간을 찾을 평가 에피소드 수 (평가 시드 1~20 전체)


def run(route, level, e, agent=None, RL=None):
    P = config_isl()
    apply_bg_level(P, level)
    P.routeName = route
    P.nodeLogEnable = False
    P.animDuration = P.simTime + P.maxDrainTime   # 큐 길이를 모든 step 기록
    G = build_grid(P)
    sample_hotspots(P, G, P.bgScenarioSeed + e)
    qvals = []
    if route == 'routeC':
        set_agent(agent, RL, explore=False)
        orig = S.ROUTE_FUNCS['routeC']

        def wrapped(*a, **k):   # C가 고를 때마다 4방향 Q값을 같이 기록 (decision_log와 같은 순서)
            out = orig(*a, **k)
            import torch
            with torch.no_grad():
                q = agent.q(torch.as_tensor(STATE.last[0]).unsqueeze(0)).squeeze(0).numpy()
            mask = STATE.last[1]
            qvals.append([round(float(v), 3) if m > 0 else None for v, m in zip(q, mask)])
            return out
        S.ROUTE_FUNCS['routeC'] = wrapped
        try:
            R = S.run_isl_sim(P, P.genRate, 0, P.randomSeed + e, True)
        finally:
            S.ROUTE_FUNCS['routeC'] = orig
    else:
        R = S.run_isl_sim(P, P.genRate, 0, P.randomSeed + e, True)
    return P, G, R, qvals


def longest_run_start(status):
    # 가장 긴 연속 손실의 (시작 패킷 번호, 길이)
    lost = np.concatenate([[0], (status != 1).astype(int), [0]])
    edge = np.diff(lost)
    starts, ends = np.flatnonzero(edge == 1), np.flatnonzero(edge == -1)
    if not starts.size:
        return 0, 0
    i = int(np.argmax(ends - starts))
    return int(starts[i]), int(ends[i] - starts[i])


def pack(R, qvals, t0, t1, linkIds):
    D = R.decisionLog
    rows = np.flatnonzero((R.genTime[D[:, 1].astype(int)] <= t1) & (R.endTime[D[:, 1].astype(int)] >= t0))
    packets = {}
    for i in rows:
        pid = int(D[i, 1])
        if pid not in packets:
            packets[pid] = dict(id=pid, gen=int(R.genTime[pid]), end=int(R.endTime[pid]), result=int(R.status[pid]), hops=[])
        hop = [int(D[i, 0]), int(D[i, 3]), int(D[i, 4]), int(D[i, 21])]
        if qvals:
            hop.append(qvals[i])
        packets[pid]['hops'].append(hop)
    queues = R.animQueue[linkIds, t0 - 1:t1].T.astype(int).tolist()   # [step][link]
    return dict(packets=sorted(packets.values(), key=lambda x: x['id']), queues=queues)


def main():
    args = sys.argv[1:]
    modelPath = args[0]
    level = args[1] if len(args) > 1 else 'severe'
    outDir = args[2] if len(args) > 2 else os.path.join(os.path.expanduser('~'), 'isl_saved_runs', f'replay_{datetime.now():%Y-%m-%d}')
    os.makedirs(outDir, exist_ok=True)

    # 1. B가 가장 길게 연속으로 잃은 에피소드와 시점 찾기
    best = None
    for e in range(SEARCH_EPISODES):
        P, G, R, _ = run('routeB', level, e)
        start, length = longest_run_start(R.status)
        print(f'에피소드 {e}: B 최대 연속 손실 {length}')
        if best is None or length > best[1]:
            best = (e, length, int(R.genTime[start]), R)
    e, length, tLoss, RD = best
    t0 = max(1, tLoss - LEAD)
    t1 = min(t0 + WINDOW - 1, RD.animQueue.shape[1])

    # 2. 같은 에피소드를 C로
    P0 = config_isl()
    RL = config_rl(P0)
    agent = DQNAgent(RL)
    agent.load(modelPath)
    P, G, RC, qvals = run('routeC', level, e, agent, RL)

    # 3. 링크 목록 (있는 링크만), 기록 묶기
    links = []
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            for d in G.validDirs[p][s]:
                links.append(dict(id=int(G.linkId[p, s, d - 1]), p=p, s=s, dir=d))
    linkIds = [l['id'] for l in links]
    data = dict(
        level=level, episode=e, seed=P.randomSeed + e, t0=t0, t1=t1, tLoss=tLoss, lossRunD=length,
        model=os.path.basename(modelPath),
        grid=dict(planes=P.numPlanes, sats=P.satsPerPlane, src=P.srcSat.tolist(), dst=P.dstSat.tolist()),
        deadline=P.deadline, queueMax=P.queueMax, linkDelay=P.linkDelay.tolist(),
        links=[dict(p=l['p'], s=l['s'], dir=l['dir']) for l in links],
        routes=dict(C=pack(RC, qvals, t0, t1, linkIds), D=pack(RD, [], t0, t1, linkIds)),
        made=f'{datetime.now():%Y-%m-%d %H:%M}')

    with open(os.path.join(outDir, 'replay_data.js'), 'w', encoding='utf-8') as f:
        f.write('window.REPLAY = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';\n')
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replay', 'replay.html'), outDir)
    print(f'에피소드 {e} (시드 {P.randomSeed + e}), 구간 {t0}~{t1} step, B 최대 연속 손실 {length}')
    print(f'저장: {outDir}')


if __name__ == '__main__':
    main()
