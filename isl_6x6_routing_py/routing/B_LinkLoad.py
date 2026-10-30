# B 라우팅 결정 - 연속 손실을 막는 것을 먼저 보고, 남은 방향 중 링크 점유율 L로 다음 방향을 고름
#
# 판단 순서 (각 단계에서 후보가 하나도 안 남으면 그 단계는 건너뜀)
#   0. 없는 방향, 큐가 꽉 찬 방향 제외
#   1. 손실 직후 회피: 최근 P.holdTime step 안에 오버플로가 난 링크 제외 (연이은 패킷이 같은 곳에서 계속 버려지는 것 차단)
#   2. 넘칠 위험 회피: 큐가 P.riskRatio 이상 찬 링크 제외
#   3. 기한 여유 확인: 링크 지연 + 큐 대기 + 다음 위성에서 목적지까지 최소 지연 > 남은 기한인 방향 제외
#   4. 남은 후보를 L 등급(Idle > Relatively Busy > Busy)으로 순위
#   5. 같은 등급이면 목적지 쪽 방향을 먼저 보고, (P.bAlternate가 True일 때만) 그중 이 위성이 직전에 고른 방향과 다른 쪽 (연이은 패킷 나누기)
#   6. 그래도 같으면 목적지까지 남은 최소 지연이 짧은 쪽, 다음은 주 경로(좌/우) > 대체 경로(상/하)
import numpy as np

from routing.A_Dijkstra import dist_to_dst


def B_LinkLoad(curP, curS, queueLen, G, P, t=0, remDeadline=None, lastDrop=None, lastDir=None, **packet):   # packet: 그 밖의 패킷 정보 (ttl, hops 등, 여기서는 안 씀)
    # 입력: 현재 위성 (curP,curS), 링크별 큐 길이 queueLen, 그리드 G, 설정 P
    #       t 현재 step, remDeadline 이 패킷의 남은 기한, lastDrop 링크별 마지막 오버플로 step, lastDir 위성별 직전 선택 방향
    # 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우)
    #       choiceType 1 주 경로, 2 대체 경로, 3 그 외 방향, 5 손실 회피 규칙(1~3단계) 때문에 방향이 바뀜
    #       L, N 4방향 링크 점유율 / 이웃 부하 (없는 방향은 -1)
    dist = dist_to_dst(G)
    dirs = list(G.validDirs[curP][curS])
    link = {d: G.linkId[curP, curS, d - 1] for d in dirs}
    nxt = {d: (curP + G.stepP[d - 1], curS + G.stepS[d - 1]) for d in dirs}

    L = [-1.0] * 4
    N = [-1.0] * 4
    for d in dirs:
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nxt[d][0]][nxt[d][1]]]))   # 이웃 부하: 다음 위성 링크 큐 평균
        V = queueLen[link[d]]                                                    # 링크 부하: 보내려는 링크 큐 길이
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax                  # 링크 점유율

    # 주 경로 = 목적지 쪽 좌/우, 대체 경로 = 목적지 쪽 상/하
    remainP = G.dstSat[0] - curP
    remainS = G.dstSat[1] - curS
    primaryDir = (3 + (remainP > 0)) if remainP != 0 else (1 + (remainS > 0))
    altDir = (1 + (remainS > 0)) if (remainP != 0 and remainS != 0) else 0
    role = {d: 0 if d == primaryDir else 1 if d == altDir else 2 for d in dirs}

    def keep(cand, ok):   # 조건을 만족하는 후보만 남기되, 하나도 없으면 그대로
        out = [d for d in cand if ok(d)]
        return out or cand

    # 0. 큐가 꽉 찬 방향 제외
    base = keep(dirs, lambda d: queueLen[link[d]] < P.queueMax)
    # 1~3. 손실 회피 규칙
    cand = base
    if lastDrop is not None:
        cand = keep(cand, lambda d: t - lastDrop[link[d]] >= P.holdTime)
    cand = keep(cand, lambda d: queueLen[link[d]] / P.queueMax < P.riskRatio)
    if remDeadline is not None:
        est = {d: G.linkDelay[link[d]] + queueLen[link[d]] / P.linkCapacity + dist[nxt[d]] for d in cand}
        cand = keep(cand, lambda d: est[d] <= remDeadline)

    nextDir = pick(cand, L, role, dist, nxt, curP, curS, lastDir, P)
    if nextDir != pick(base, L, role, dist, nxt, curP, curS, lastDir, P):
        choiceType = 5   # 손실 회피 규칙이 없었다면 다른 방향을 골랐음
    else:
        choiceType = 1 + role[nextDir]
    return nextDir, choiceType, L, N


def pick(cand, L, role, dist, nxt, curP, curS, lastDir, P):
    # 4. L 등급이 가장 좋은 후보만 남김
    best = min(link_state(L[d - 1], P) for d in cand)
    pool = [d for d in cand if link_state(L[d - 1], P) == best]
    # 5. 목적지 쪽 방향을 먼저, 그중 직전 선택과 다른 방향 (연이은 패킷 나누기)
    toward = [d for d in pool if dist[nxt[d]] < dist[curP, curS]]
    pool = toward or pool
    if getattr(P, 'bAlternate', False) and lastDir is not None and len(pool) > 1:   # 연이은 패킷 나누기 (기본 꺼짐)
        pool = [d for d in pool if d != lastDir[curP, curS]] or pool
    # 6. 남은 최소 지연, 다음은 주 경로 > 대체 경로 > 나머지
    return min(pool, key=lambda d: (dist[nxt[d]], role[d]))


def link_state(L, P):
    # 1 Idle, 2 Relatively Busy, 3 Busy
    if L < P.X:
        return 1
    elif L < P.Y:
        return 2
    return 3
