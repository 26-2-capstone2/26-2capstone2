# 주 흐름 여러 개 - 에피소드마다 실시간 UDP 흐름 목록(출발 위성, 도착 위성)을 정함
#
# 흐름 0 = 측정 흐름: 성능(도착률, 연속 손실)을 재는 흐름. 우리 GSL에서 들어와 망의 가장 먼 곳까지 가는 장거리 흐름
#   검증, 최종 평가 (P.flowZeroRandom = False): P.srcSat -> P.dstSat 고정 (격자에서 가장 먼 쌍, 6x6이면 (0,0) -> (5,5))
#   학습 (P.flowZeroRandom = True):          최소 지연이 "측정 흐름의 최소 지연 x P.mainFarFrac" 이상인 쌍 중 무작위
#     -> 시험과 같은 장거리를 연습하되, 출발 위성이 매번 바뀌어 경로 하나를 외우지 못하게 함
# 흐름 1 ~ numFlows-1 = 다른 GSL 흐름: 다른 지역 지상국 사용자의 트래픽 (C가 같이 라우팅, 보조 지표)
#   최소 지연이 "가장 먼 거리 x P.otherFlowFracMin" ~ 가장 먼 거리인 쌍 중 무작위
#   거리 구간을 P.otherFlowBands개로 나눠 흐름마다 구간을 고르게 뽑음 (짧은, 중간, 먼 흐름이 골고루 섞이게.
#   쌍을 그냥 뽑으면 중간 거리 쌍이 가장 많아 그쪽으로 쏠림)
# 모든 흐름 공통: 최소 홉 수가 측정 흐름(P.srcSat -> P.dstSat)의 최소 홉 수 이하, 최소 지연이 (기한 - DEADLINE_MARGIN) 이하인 쌍만 씀
#   (TTL, 기한은 측정 흐름 기준으로 정해지므로, 다른 흐름도 같거나 더 넉넉한 홉, 시간 여유를 갖게 함)
#   "가장 먼 거리" = 이 조건을 만족하는 쌍 중 최소 지연이 가장 큰 값 (6x6, Starlink는 측정 흐름과 같음)
#   흐름끼리 출발 위성, 도착 위성이 겹치지 않게 뽑음
#   출발, 도착을 시드로 뽑음 (같은 시드면 같은 흐름 -> B, C를 같은 조건에서 비교)
#   에피소드(10초) 안에서는 고정 (위성 핸드오버는 몇 분 단위라 한 연결로 봄)
# 흐름마다 초당 P.genRate개 (GSL 세션 하나와 같은 값)
import heapq

import numpy as np

_TABLES = {}   # 망 구조별 쌍 표 (한 번만 계산. Starlink는 처음 한 번에 수십 초)


def _grid_key(G):
    return (G.hasLink.shape, G.hasLink.tobytes(), np.asarray(G.linkDelay).tobytes(),
            np.asarray(G.nextP).tobytes(), np.asarray(G.nextS).tobytes())


def pair_table(G):
    # 모든 (출발, 도착) 쌍의 최소 지연(step)과 최소 홉 수. 반환: delay[dp, ds, sp, ss], hops[dp, ds, sp, ss]
    key = _grid_key(G)
    if key in _TABLES:
        return _TABLES[key]
    numP, numS = G.hasLink.shape[:2]
    incoming = [[[] for _ in range(numS)] for _ in range(numP)]   # (p,s)로 들어오는 링크: (출발 위성, 지연)
    for q in range(numP):
        for r in range(numS):
            for d in G.validDirs[q][r]:
                l = int(G.linkId[q, r, d - 1])
                incoming[int(G.nextP[l])][int(G.nextS[l])].append((q, r, int(G.linkDelay[l])))
    delay = np.full((numP, numS, numP, numS), np.inf)
    hops = np.full((numP, numS, numP, numS), np.inf)
    for dp in range(numP):
        for ds in range(numS):
            dist = delay[dp, ds]
            dist[dp, ds] = 0
            heap = [(0, dp, ds)]
            while heap:   # 목적지에서 거꾸로 퍼지는 Dijkstra (최소 지연)
                c, p, s = heapq.heappop(heap)
                if c > dist[p, s]:
                    continue
                for q, r, w in incoming[p][s]:
                    if c + w < dist[q, r]:
                        dist[q, r] = c + w
                        heapq.heappush(heap, (c + w, q, r))
            h = hops[dp, ds]
            h[dp, ds] = 0
            frontier = [(dp, ds)]
            k = 0
            while frontier:   # 목적지에서 거꾸로 퍼지는 BFS (최소 홉)
                k += 1
                nxt = []
                for p, s in frontier:
                    for q, r, _ in incoming[p][s]:
                        if h[q, r] == np.inf:
                            h[q, r] = k
                            nxt.append((q, r))
                frontier = nxt
    _TABLES[key] = (delay, hops)
    return delay, hops


_CANDS = {}


def flow_candidates(P, G):
    # 반환: 가장 먼 거리(step), 측정 흐름 학습 후보, 다른 GSL 흐름 후보 (각각 배열 (출발 p, 출발 s, 도착 p, 도착 s, 지연))
    # 망 구조와 설정이 같으면 한 번만 계산해 보관
    from sim.topology import DEADLINE_MARGIN
    key = (_grid_key(G), tuple(int(x) for x in P.srcSat), tuple(int(x) for x in P.dstSat), int(P.deadline),
           float(getattr(P, 'mainFarFrac', 0.9)), float(getattr(P, 'otherFlowFracMin', 0.25)))
    if key in _CANDS:
        return _CANDS[key]
    delay, hops = pair_table(G)
    src0 = (int(P.srcSat[0]), int(P.srcSat[1]))
    dst0 = (int(P.dstSat[0]), int(P.dstSat[1]))
    hopLimit = hops[dst0[0], dst0[1], src0[0], src0[1]]           # 측정 흐름의 최소 홉 수
    mainDelay = float(delay[dst0[0], dst0[1], src0[0], src0[1]])   # 측정 흐름(시험)의 최소 지연
    delayLimit = P.deadline - DEADLINE_MARGIN                      # 기한 여유를 측정 흐름과 같거나 더 넉넉하게
    ok = np.isfinite(delay) & (delay > 0) & (delay <= delayLimit) & (hops <= hopLimit)
    maxDelay = float(delay[ok].max())
    farMin = mainDelay * float(getattr(P, 'mainFarFrac', 0.9))
    otherMin = maxDelay * float(getattr(P, 'otherFlowFracMin', 0.25))

    def table(mask):
        dp, ds, sp, ss = np.nonzero(mask)
        return np.column_stack([sp, ss, dp, ds, delay[dp, ds, sp, ss]])

    out = (maxDelay, table(ok & (delay >= farMin)), table(ok & (delay >= otherMin)))
    _CANDS[key] = out
    return out


def make_flows(P, G, seed):
    # 반환: [((출발 p, 출발 s), (도착 p, 도착 s)), ...] 길이 P.numFlows (0번 = 측정 흐름)
    fixed = ((int(P.srcSat[0]), int(P.srcSat[1])), (int(P.dstSat[0]), int(P.dstSat[1])))
    numFlows = int(getattr(P, 'numFlows', 1))
    zeroRandom = bool(getattr(P, 'flowZeroRandom', False))
    if numFlows <= 1 and not zeroRandom:
        return [fixed]
    rng = np.random.RandomState(int(seed) + 300000)   # 배경 트래픽 난수와 다른 난수열

    def pair(row):
        return (int(row[0]), int(row[1])), (int(row[2]), int(row[3]))

    maxDelay, main, other = flow_candidates(P, G)
    if zeroRandom:
        if not len(main):
            raise ValueError('측정 흐름 학습 후보(측정 흐름 거리 근처 쌍)가 없습니다')
        flows = [pair(main[rng.randint(len(main))])]
    else:
        flows = [fixed]
    if numFlows <= 1:
        return flows
    if not len(other):
        raise ValueError('다른 GSL 흐름 후보가 없습니다')
    nb = max(1, int(getattr(P, 'otherFlowBands', 3)))
    lo = float(other[:, 4].min())
    width = (maxDelay - lo) / nb if maxDelay > lo else 1.0
    band = np.minimum(nb - 1, ((other[:, 4] - lo) / width).astype(int))
    bands = [np.flatnonzero(band == b) for b in range(nb)]
    bands = [b for b in bands if len(b)]
    for _ in range(100000):
        if len(flows) >= numFlows:
            break
        idx = bands[rng.randint(len(bands))]
        src, dst = pair(other[idx[rng.randint(len(idx))]])
        if any(src == a or dst == b for a, b in flows):   # 다른 흐름과 출발 위성이나 도착 위성이 겹치면 다시 뽑음
            continue
        flows.append((src, dst))
    else:
        raise ValueError('서로 겹치지 않는 흐름을 만들지 못했습니다')
    return flows
