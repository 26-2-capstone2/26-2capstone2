# A 라우팅 결정 (route_A) - 링크 지연 합이 가장 작은 경로(최단 경로)로만 보냄, 부하(큐)는 보지 않음 (기준선)
#
import heapq

import numpy as np

TIE_ORDER = [4, 3, 2, 1]   # 최단 경로가 여러 개면 우 > 좌 > 하 > 상 순서 (좌/우 먼저, route_B 주 경로와 같은 규칙)


def route_A(curP, curS, queueLen, G, P, **packet):   # packet: B가 쓰는 패킷 정보 (여기서는 안 씀)
    # A: 최단 경로 라우팅 (링크 지연을 가중치로 한 Dijkstra, 부하 무시)
    # 입력/출력은 route_B와 같음 (나중에 run_isl_sim에서 바꿔 끼우기 쉽게)
    # 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우), choiceType = 1 (항상 최단 경로)
    #       L, N 4방향 링크 점유율 / 이웃 부하 (결정에는 안 쓰고 decision_log 상태 기록용, 없는 방향은 -1)
    dist = dist_to_dst(G)

    L = [-1.0] * 4
    N = [-1.0] * 4
    for d in G.validDirs[curP][curS]:   # route_B와 같은 계산 (기록용)
        nextP, nextS = G.nbrP[curP, curS, d - 1], G.nbrS[curP, curS, d - 1]   # 이웃 위성 (원형 연결 반영)
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))
        V = queueLen[G.linkId[curP, curS, d - 1]]
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax

    # 다음 위성까지 링크 지연 + 다음 위성에서 목적지까지 최소 지연이 가장 작은 방향
    nextDir, best = 0, np.inf
    for d in TIE_ORDER:
        if d not in G.validDirs[curP][curS]:
            continue
        cost = G.linkDelay[G.linkId[curP, curS, d - 1]] + dist[G.nbrP[curP, curS, d - 1], G.nbrS[curP, curS, d - 1]]
        if cost < best:   # 같으면 TIE_ORDER 앞쪽 유지
            nextDir, best = d, cost
    return nextDir, 1, L, N


def dist_to_dst(G):
    # 모든 위성 -> 지금 목적지(G.dstSat) 최소 지연 합 (step). 목적지별로 처음 한 번만 계산해 G에 저장
    # 흐름이 여러 개면 시뮬레이터가 패킷마다 G.dstSat을 그 패킷의 도착 위성으로 바꿔 놓고 라우팅을 부름
    key = (int(G.dstSat[0]), int(G.dstSat[1]))
    cache = G.__dict__.setdefault('distCache', {})
    if key not in cache:
        cache[key] = _dist_to(G, key)
    return cache[key]


def _dist_to(G, dst):
    numP, numS = G.hasLink.shape[:2]
    dist = np.full((numP, numS), np.inf)
    dist[dst[0], dst[1]] = 0
    link_src = {}
    incoming = {(p, s): [] for p in range(numP) for s in range(numS)}
    for q in range(numP):
        for r in range(numS):
            for d in G.validDirs[q][r]:
                l = int(G.linkId[q, r, d - 1])
                link_src[l] = (q, r)
                incoming[(int(G.nextP[l]), int(G.nextS[l]))].append(l)
    heap = [(0, dst[0], dst[1])]
    while heap:   # 목적지에서 거꾸로 퍼져 나가는 Dijkstra (링크 a->b 비용으로 a의 거리 갱신)
        dd, p, s = heapq.heappop(heap)
        if dd > dist[p, s]:
            continue
        for l in incoming[(p, s)]:   # (p,s)로 들어오는 링크 l: 이웃 (q,r)에서 출발 (원형 연결 포함)
            q, r = link_src[l]
            nd = dd + G.linkDelay[l]
            if nd < dist[q, r]:
                dist[q, r] = nd
                heapq.heappush(heap, (nd, int(q), int(r)))
    return dist
