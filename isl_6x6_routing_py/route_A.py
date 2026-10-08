# A 라우팅 결정 - 링크 지연 합이 가장 작은 경로(최단 경로)로만 보냄, 부하(큐)는 보지 않음 (기준선)
#
import heapq

import numpy as np

TIE_ORDER = [4, 3, 2, 1]   # 최단 경로가 여러 개면 우 > 좌 > 하 > 상 순서 (좌/우 먼저, route_B 주 경로와 같은 규칙)


def route_A(curP, curS, queueLen, G, P):
    # A: 최단 경로 라우팅 (링크 지연을 가중치로 한 Dijkstra, 부하 무시)
    # 입력/출력은 route_B와 같음 (나중에 run_isl_sim에서 바꿔 끼우기 쉽게)
    # 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우), choiceType = 1 (항상 최단 경로)
    #       L, N 4방향 링크 점유율 / 이웃 부하 (결정에는 안 쓰고 decision_log 상태 기록용, 없는 방향은 -1)
    dist = dist_to_dst(G)

    L = [-1.0] * 4
    N = [-1.0] * 4
    for d in G.validDirs[curP][curS]:   # route_B와 같은 계산 (기록용)
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))
        V = queueLen[G.linkId[curP, curS, d - 1]]
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax

    # 다음 위성까지 링크 지연 + 다음 위성에서 목적지까지 최소 지연이 가장 작은 방향
    nextDir, best = 0, np.inf
    for d in TIE_ORDER:
        if d not in G.validDirs[curP][curS]:
            continue
        cost = G.linkDelay[G.linkId[curP, curS, d - 1]] + dist[curP + G.stepP[d - 1], curS + G.stepS[d - 1]]
        if cost < best:   # 같으면 TIE_ORDER 앞쪽 유지
            nextDir, best = d, cost
    return nextDir, 1, L, N


def dist_to_dst(G):
    # 모든 위성 -> 목적지 최소 지연 합 (step). Grid가 바뀌지 않으니 처음 한 번만 계산해 G에 저장
    if getattr(G, 'distToDst', None) is not None:
        return G.distToDst
    numP, numS = G.hasLink.shape[:2]
    dist = np.full((numP, numS), np.inf)
    dist[G.dstSat[0], G.dstSat[1]] = 0
    heap = [(0, int(G.dstSat[0]), int(G.dstSat[1]))]
    while heap:   # 목적지에서 거꾸로 퍼져 나가는 Dijkstra (링크 a->b 비용으로 a의 거리 갱신)
        dd, p, s = heapq.heappop(heap)
        if dd > dist[p, s]:
            continue
        for d in range(1, 5):   # (p,s)로 들어오는 링크: 이웃 (q,r)에서 방향 d로 (p,s)에 도착
            q, r = p - G.stepP[d - 1], s - G.stepS[d - 1]
            if 0 <= q < numP and 0 <= r < numS and G.hasLink[q, r, d - 1]:
                nd = dd + G.linkDelay[G.linkId[q, r, d - 1]]
                if nd < dist[q, r]:
                    dist[q, r] = nd
                    heapq.heappush(heap, (nd, int(q), int(r)))
    G.distToDst = dist
    return dist
