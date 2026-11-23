# 라우팅 비교 화면(compare.html)용 데이터 - 같은 시나리오(망, 혼잡 단계, 시드)를 DRA(routeB)와 RL(routeC)로 한 번씩 돌려 재생용 기록을 만듦
#
# 같은 시드면 주 흐름, 핫스팟, 패킷 생성이 똑같음 -> 패킷 번호끼리 바로 비교할 수 있음 (eval_routes.py의 평가 시드와 같은 조건)
# 재생 기록 (라우팅마다)
#   frames: FRAME step마다 [시각, 붐비는 링크 쌍 [[쌍 번호, 큐], ...], 이동 중인 흐름 0 패킷 [[출발 위성, 지금 위성], ...]]
#   흐름 0 패킷마다: 결과(status), 생성 시각, 끝난 시각, 지나간 위성 목록, 손실 위치
#   핫스팟 일정(두 라우팅 공통), 지표 (도착률, 연속 손실, 최대 연속 손실, 평균 지연, 평균 홉)
import os

import numpy as np

from analysis.burst_summary import burst_summary
from config_isl import apply_bg_level
from routing.route_C import set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim
from web.schema import build_config, map_data

FRAME = 20             # 재생 한 장 = 20 ms (10초 = 500장)
QUEUE_SHOW = 40        # 이 큐 길이 이상인 링크만 보냄 (지도에 진하게 칠할 것만)
_CACHE = {}


def list_models():
    # rl_models 아래 model_final.pt (최근 것이 위). 이름 = rl_models 기준 상대 경로
    from web.results import train_root
    root = train_root()
    out = []
    for dirpath, dirs, files in os.walk(root):
        if dirpath[len(root):].count(os.sep) > 2:
            dirs[:] = []
            continue
        if 'model_final.pt' in files:
            f = os.path.join(dirpath, 'model_final.pt')
            out.append(dict(name=os.path.relpath(dirpath, root).replace(os.sep, '/'), time=os.path.getmtime(f)))
    return sorted(out, key=lambda r: -r['time'])


def _run_one(route, P, G, seed, pairOf, linkIds, S):
    rec = dict(frames=[], lossPos={})
    linkFrom = {}
    for p in range(P.numPlanes):
        for s in range(S):
            for d in G.validDirs[p][s]:
                linkFrom[int(G.linkId[p, s, d - 1])] = p * S + s
    numPairs = int(pairOf.max()) + 1
    prev = [None]

    def hook(t, queueLen, status, curP, curS, onLink, numPackets):
        seq = numPackets // P.numFlows
        st0 = status[:seq]
        if prev[0] is not None:   # 새로 손실된 흐름 0 패킷의 위치 (지도에 X)
            n0 = len(prev[0])
            for i in np.flatnonzero((st0[:n0] != prev[0]) & (st0[:n0] >= 2)):
                rec['lossPos'][int(i)] = int(curP[i]) * S + int(curS[i])
        prev[0] = st0.copy()
        if t % FRAME:
            return
        q = np.zeros(numPairs, dtype=int)
        np.maximum.at(q, pairOf, queueLen[linkIds].astype(int))
        busy = np.flatnonzero(q >= QUEUE_SHOW)
        pk = []
        for i in np.flatnonzero(st0 == 0):
            cur = int(curP[i]) * S + int(curS[i])
            l = int(onLink[i])
            pk.append([linkFrom.get(l, cur) if l >= 0 else cur, cur])
        rec['frames'].append([int(t), [[int(k), int(q[k])] for k in busy], pk])

    P.routeName = route
    P.stepHook = hook
    try:
        R = run_isl_sim(P, P.genRate, 0, seed, False)
    finally:
        P.stepHook = None
    n0 = P.flowBlock
    st = R.status[:n0].astype(int)
    D = R.decisionLog
    D0 = D[D[:, 1] < n0]
    paths = [[] for _ in range(n0)]
    for pid, p, s in D0[:, [1, 3, 4]].astype(int):
        paths[pid].append(int(p) * S + int(s))
    for pid in range(n0):   # 도착한 패킷은 목적지 위성까지 이어 그림
        if st[pid] in (1, 2):
            paths[pid].append(int(P.dstSat[0]) * S + int(P.dstSat[1]))
    b = burst_summary(st, P.burstMinLen)
    on = st == 1
    lat = (R.endTime[:n0] - R.genTime[:n0])[on]
    minutes = P.simTime * P.stepTime / 60
    rec.update(status=st.tolist(), gen=R.genTime[:n0].astype(int).tolist(), end=R.endTime[:n0].astype(int).tolist(),
               paths=paths, lossPos=rec['lossPos'],
               metrics=dict(onTime=round(on.mean() * 100, 1), lossRate=round((st >= 2).mean() * 100, 1),
                            burstCount=int(b.burstCount), burstPerMin=round(b.burstCount / minutes, 1),
                            maxConsec=int(b.maxConsecLoss), burstShare=round(b.burstPackets / max(1, (st >= 2).sum()) * 100, 1),
                            latency=round(float(lat.mean()) * P.stepTime * 1000, 1) if lat.size else None,
                            hops=round(float(np.mean([len(x) - 1 for x, o in zip(paths, on) if o])), 1) if on.any() else None))
    return rec


def run_compare(topology, level, seed, model, saved=None):
    key = (topology, level, seed, model)
    if key in _CACHE:
        return _CACHE[key]
    from rl.rl_agent import DQNAgent   # PyTorch는 이 화면을 쓸 때만 필요
    from web.results import train_root
    overrides = dict(saved or {}, topology=topology)
    P, RL = build_config(overrides)
    apply_bg_level(P, level)
    G = build_grid(P)
    view, linkIds, pairOf = map_data(P, G)
    S = P.satsPerPlane
    path = os.path.realpath(os.path.join(train_root(), model, 'model_final.pt'))
    if not path.startswith(os.path.realpath(train_root()) + os.sep) or not os.path.exists(path):
        raise ValueError(f'모델이 없음: {model}')
    agent = DQNAgent(RL)
    agent.load(path)
    set_agent(agent, RL, explore=False)
    out = dict(topology=topology, level=level, seed=seed, model=model, map=view, frame=FRAME, simTime=P.simTime,
               queueMax=P.queueMax, burstMinLen=P.burstMinLen, routes={})
    for name, route in (('DRA', 'routeB'), ('RL', 'routeC')):
        sample_hotspots(P, G, seed)   # 주 흐름과 핫스팟을 시드로 다시 정함 (두 라우팅이 같은 시나리오)
        out['routes'][name] = _run_one(route, P, G, seed, np.array(pairOf), np.array(linkIds), S)
    f0 = P.mainFlows[0]
    out['flow0'] = dict(src=[int(f0[0][0]), int(f0[0][1])], dst=[int(f0[1][0]), int(f0[1][1])],
                        deadline=int(P.mainDeadlines[0]) if getattr(P, 'mainDeadlines', None) is not None else int(P.deadline))
    # 지역 핫스팟 일정: [링크 쌍 번호, 시작 ms, 끝 ms, 중심 위성] (live._begin_episode와 같은 방식)
    pairIdx = {tuple(sorted(pr)): k for k, pr in enumerate(view['pairs'])}
    hot = []
    for ((sp, ss), (np_, ns_)), (a, b) in zip(P.bgFlows, P.bgEvents):
        if (a, b) == (1, P.simTime):
            continue
        k = pairIdx.get(tuple(sorted((int(sp) * S + int(ss), int(np_) * S + int(ns_)))))
        if k is not None:
            hot.append([k, int(a), int(b), int(sp) * S + int(ss)])
    out['hotspots'] = hot
    if len(_CACHE) > 6:
        _CACHE.clear()
    _CACHE[key] = out
    return out
