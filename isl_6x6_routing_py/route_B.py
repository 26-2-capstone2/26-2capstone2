# B 라우팅 결정 - DRA (Datagram Routing Algorithm, Ekici·Akyildiz·Bender 2001)를 이 6x6 Grid에 맞게 옮긴 것
#
# DRA: 극궤도 격자형 LEO 위성망(이리듐형)을 위한 분산 라우팅
#   - 각 위성이 패킷마다 따로 결정, 위성끼리 상태 정보를 주고받지 않음 (자기 송신 큐만 봄)
#   - 원 논문의 3단계를 이 Grid에 맞게 적용
#     (1) 방향 추정: 목적지까지 최소 홉이 되는 좌/우 방향, 상/하 방향을 구함 (뒤로 가는 방향은 쓰지 않음)
#     (2) 방향 개선: 둘 중 하나를 주(primary), 다른 하나를 보조(secondary)로 정함
#         원 논문은 위도에 따라 궤도 간 링크 길이가 달라지는 것을 보고 정하지만,
#         이 Grid는 링크 지연이 위치와 상관없이 일정해서(상/하 7, 좌/우 2) 어느 순서든 총 지연이 같음
#         -> 좌/우를 주 방향으로 고정 (route_A의 동점 규칙, 배경 XY 경로와 같은 순서)
#     (3) 혼잡 회피: 송신 큐 길이 >= 임계값이면 '혼잡'
#         - 보조 방향이 없으면 주 방향
#         - 주 방향이 혼잡하지 않으면 주 방향
#         - 주 방향이 혼잡하고 보조 방향이 혼잡하지 않으면 보조 방향
#         - 둘 다 혼잡하면 주 방향 (원 논문 규칙, 우회하지 않음)
#   - 임계값: P.draThreshold x P.queueMax (원 논문은 숫자를 밝히지 않아 설정값으로 둠)
#   원 논문의 극지방/seam 규칙과 링크 고장 시 우회는 이 Grid에 없으므로 생략
#
# 입력: 현재 위성 (curP,curS), 링크별 큐 길이 queueLen, 그리드 G, 설정 P
# 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우), choiceType 선택 유형(1 주, 2 보조)
#       L, N 4방향 링크 점유율 / 이웃 부하 (결정에는 안 쓰고 decision_log 기록용, 없는 방향은 -1)
# 나중에 강화학습으로 바꿀 때는 이 함수만 교체하면 됨
import numpy as np


def route_B(curP, curS, queueLen, G, P):
    # decision_log 기록용 상태 (route_A와 같은 계산, 결정에는 안 씀)
    L = [-1.0] * 4
    N = [-1.0] * 4
    for d in G.validDirs[curP][curS]:
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))   # 이웃 부하
        V = queueLen[G.linkId[curP, curS, d - 1]]                        # 링크 부하 (송신 큐 길이)
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax          # 링크 점유율

    # (1)(2) 방향 추정 + 주/보조 방향: 좌/우가 주, 상/하가 보조 (둘 다 목적지에 가까워지는 방향)
    remainP = G.dstSat[0] - curP
    remainS = G.dstSat[1] - curS
    horiz = (4 if remainP > 0 else 3) if remainP != 0 else 0   # 4 우, 3 좌
    vert = (2 if remainS > 0 else 1) if remainS != 0 else 0    # 2 하, 1 상
    primaryDir, secondaryDir = (horiz, vert) if horiz else (vert, 0)

    # (3) 혼잡 회피: 자기 송신 큐만 봄
    if secondaryDir == 0:
        return primaryDir, 1, L, N
    threshold = P.draThreshold * P.queueMax
    primBusy = queueLen[G.linkId[curP, curS, primaryDir - 1]] >= threshold
    secBusy = queueLen[G.linkId[curP, curS, secondaryDir - 1]] >= threshold
    if primBusy and not secBusy:
        return secondaryDir, 2, L, N
    return primaryDir, 1, L, N
