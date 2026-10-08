# B 라우팅 결정 - 링크 점유율 L로 주/대체/우회 경로 중 다음 방향을 고름 
#
import math

import numpy as np


def route_B(curP, curS, queueLen, G, P):
    # B: 트래픽 부하 고려 라우팅 (Liu et al. 단순화)
    # 입력: 현재 위성 (curP,curS), 링크별 큐 길이 queueLen, 그리드 G, 설정 P
    # 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우), choiceType 선택 유형(1 주, 2 대체, 3 우회)
    #       L, N 4방향 링크 점유율 / 이웃 부하 (없는 방향은 -1)
    # 나중에 강화학습으로 바꿀 때는 이 함수만 교체하면 됨
    L = [-1.0] * 4
    N = [-1.0] * 4
    for d in G.validDirs[curP][curS]:
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))   # 이웃 부하 N_n(t)
        V = queueLen[G.linkId[curP, curS, d - 1]]                        # 링크 부하 V_mn(t) = q_mn(t)
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax          # 링크 점유율 L

    # (1) 주 경로 / 대체 경로: 좌/우 우선
    remainP = G.dstSat[0] - curP
    remainS = G.dstSat[1] - curS
    if remainP != 0:
        primaryDir = 3 + (remainP > 0)
        altDir = 1 + (remainS > 0) if remainS != 0 else 0
    else:
        primaryDir = 1 + (remainS > 0)
        altDir = 0

    # (2) 링크 상태 판정, (3) 다음 홉 선택
    primState = link_state(L[primaryDir - 1], P)
    altState = link_state(L[altDir - 1], P) if altDir > 0 else math.inf

    if primState == 1:
        nextDir, choiceType = primaryDir, 1
    elif primState == 2:
        if altState == 1:
            nextDir, choiceType = altDir, 2
        else:
            nextDir, choiceType = primaryDir, 1
    else:
        if altState <= 2:
            nextDir, choiceType = altDir, 2
        else:
            # 둘 다 혼잡 또는 대체 경로 없음: 모든 방향 중 L 최소 (동점이면 주 > 대체 > 나머지)
            cand = [primaryDir, altDir] + [d for d in range(1, 5) if d not in (primaryDir, altDir)]
            cand = [d for d in cand if d > 0 and d in G.validDirs[curP][curS]]
            i = int(np.argmin([L[d - 1] for d in cand]))
            nextDir, choiceType = cand[i], 3
    return nextDir, choiceType, L, N


def link_state(L, P):
    # 1 Idle, 2 Relatively Busy, 3 Busy
    if L < P.X:
        return 1
    elif L < P.Y:
        return 2
    return 3
