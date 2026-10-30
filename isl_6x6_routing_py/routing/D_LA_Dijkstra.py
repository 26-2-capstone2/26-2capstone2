# 최종 비교군 라우팅 알고리즘 D_LA_Dijkstra (Dijkstra + 링크부하)
#
import numpy as np

from routing.A_Dijkstra import TIE_ORDER, dist_to_dst


def D_LA_Dijkstra(curP, curS, queueLen, G, P, **packet):   # packet: B가 쓰는 패킷 정보 (여기서는 안 씀)
    dist = dist_to_dst(G)

    L = [-1.0] * 4
    N = [-1.0] * 4
    cost = {}
    full = {}
    for d in G.validDirs[curP][curS]:
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        link = G.linkId[curP, curS, d - 1]
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))
        V = queueLen[link]
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax
        cost[d] = G.linkDelay[link] + V / P.linkCapacity + N[d - 1] / P.linkCapacity + dist[nextP, nextS]
        full[d] = V >= P.queueMax

    # 후보: 목적지에 가까워지는 방향(남은 최소 지연이 줄어듦) 중 큐가 안 찬 곳 -> 없으면 안 찬 모든 방향 -> 없으면 전부
    # (가까워지는 방향을 먼저 보지 않으면 두 위성 사이를 왔다 갔다 하다 TTL 만료됨)
    closer = {d for d in cost if dist[curP + G.stepP[d - 1], curS + G.stepS[d - 1]] < dist[curP, curS]}
    cand = ([d for d in TIE_ORDER if d in closer and not full[d]]
            or [d for d in TIE_ORDER if d in cost and not full[d]]
            or [d for d in TIE_ORDER if d in cost])
    nextDir = min(cand, key=lambda d: cost[d])   # 같으면 TIE_ORDER 앞쪽 (우 > 좌 > 하 > 상)

    # 부하가 없을 때의 최단 경로 방향 (A와 같은 규칙)과 비교
    shortest = min((d for d in TIE_ORDER if d in cost),
                   key=lambda d: G.linkDelay[G.linkId[curP, curS, d - 1]] + dist[curP + G.stepP[d - 1], curS + G.stepS[d - 1]])
    choiceType = 1 if nextDir == shortest else 3
    return nextDir, choiceType, L, N
