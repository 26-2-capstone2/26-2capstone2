# 6x6 Grid 생성 - 위성 좌표, 상/하/좌/우 링크, 링크별 지연, 다음 위성을 만듦
# 실제 위성군(Iridium, Starlink)도 같은 함수로 만듦: 원형 연결, 극지방 링크 끄기, 거리 기반 지연 (sim/topology.py)
#
# 흐름: (1) 방향 정의 -> (2) 링크 번호표 -> (3) 빈 표 준비 -> (4) 위성 x 방향마다 링크 채우기 -> (5) 출발/도착 저장
# 결과 G는 run_isl_sim, route_A, route_B, node_log가 "이 위성에서 이 방향으로 가면 어디로, 몇 step?"을 찾을 때 씀
from types import SimpleNamespace

import numpy as np

from sim.topology import link_delay_steps, link_enabled


def build_grid(P):
    # 6x6 Grid 링크 구조 생성 (Grid 끝은 반대편과 연결하지 않음)
    # 방향 번호: 1 상(s-1), 2 하(s+1), 3 좌(p-1), 4 우(p+1)
    G = SimpleNamespace()
    P.topology = getattr(P, 'topology', 'grid')       # 설정에 없으면 지금까지와 같은 6x6 가상 격자
    G.wrapP = bool(getattr(P, 'wrapP', False))        # 좌/우 끝이 반대편과 이어지는지 (원형)
    G.wrapS = bool(getattr(P, 'wrapS', False))        # 상/하 끝이 반대편과 이어지는지 (같은 궤도는 원형)
    G.numP, G.numS = P.numPlanes, P.satsPerPlane

    # (1) 방향 정의: 방향 d로 한 칸 가면 좌표가 얼마나 바뀌는지 (인덱스 0~3 = 방향 1~4)
    #     예) 우(4): stepP[3] = +1, stepS[3] = 0  ->  (p,s) -> (p+1, s)
    G.stepP = np.array([0, 0, -1, 1])      # 방향별 p 변화량
    G.stepS = np.array([-1, 1, 0, 0])      # 방향별 s 변화량

    # (2) 링크 번호표: 모든 (위성, 방향) 칸에 번호를 하나씩 붙임 (6 x 6 x 4 = 144칸)
    #     Grid 끝이라 실제로 없는 링크 칸도 번호는 있음 -> 아래 hasLink, nextP = -1로 구분 (실제 링크는 120개)
    #     큐(queueLen 등)와 기록은 전부 이 링크 번호로 찾음
    G.numLinks = P.numPlanes * P.satsPerPlane * 4
    # 링크 번호 = (p,s,방향) - MATLAB과 같은 순서(열 우선)로 번호를 매김
    G.linkId = np.arange(G.numLinks).reshape((P.numPlanes, P.satsPerPlane, 4), order='F')

    # (3) 빈 표 준비: 아래 반복문에서 채움
    G.hasLink = np.zeros((P.numPlanes, P.satsPerPlane, 4), dtype=bool)   # 그 방향에 링크가 있는지
    G.nextP = np.full(G.numLinks, -1)          # 링크 끝 위성 p (-1: 링크 없음)
    G.nextS = np.full(G.numLinks, -1)          # 링크 끝 위성 s
    G.linkDelay = np.zeros(G.numLinks, dtype=int)   # 링크 지연 (step)
    G.validDirs = [[None] * P.satsPerPlane for _ in range(P.numPlanes)]   # 위성별 갈 수 있는 방향 목록
    G.outLinks = [[None] * P.satsPerPlane for _ in range(P.numPlanes)]    # 위성별 나가는 링크 번호 목록
    G.nbrP = np.full((P.numPlanes, P.satsPerPlane, 4), -1)   # 방향별 이웃 위성 좌표 (-1: 링크 없음, 원형 연결 반영)
    G.nbrS = np.full((P.numPlanes, P.satsPerPlane, 4), -1)

    # (4) 위성 36개 x 방향 4개를 하나씩 보면서 링크 채우기
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            for d in range(1, 5):
                np_ = p + G.stepP[d - 1]   # 이 방향으로 갔을 때 도착하는 위성 좌표
                ns = s + G.stepS[d - 1]
                if G.wrapP:                # 원형이면 반대편으로 이어짐
                    np_ %= P.numPlanes
                if G.wrapS:
                    ns %= P.satsPerPlane
                if 0 <= np_ < P.numPlanes and 0 <= ns < P.satsPerPlane and link_enabled(P, p, s, d):   # Grid 안이고 켜진 링크면 있음
                    G.hasLink[p, s, d - 1] = True
                    l = G.linkId[p, s, d - 1]
                    G.nextP[l] = np_               # 링크 l을 타면 도착하는 위성
                    G.nextS[l] = ns
                    G.nbrP[p, s, d - 1], G.nbrS[p, s, d - 1] = np_, ns
                    G.linkDelay[l] = link_delay_steps(P, s, d)   # 가상 격자: 상/하 7 step, 좌/우 2 step (config_isl), 실제 위성군: 거리로 계산
            # 이 위성에서 갈 수 있는 방향과 그 링크 번호 (모서리 2개, 가장자리 3개, 안쪽 4개)
            G.validDirs[p][s] = [d for d in range(1, 5) if G.hasLink[p, s, d - 1]]
            G.outLinks[p][s] = np.array([G.linkId[p, s, d - 1] for d in G.validDirs[p][s]])

    # (5) 출발/도착 위성 (route_A, route_B가 목적지 방향을 계산할 때 사용)
    G.srcSat = P.srcSat.copy()
    G.dstSat = P.dstSat.copy()
    G.maxLinkDelay = int(G.linkDelay.max())
    return G


def displacement(G, p, s, toP, toS):
    # (p, s)에서 (toP, toS)까지 칸 차이 (부호 = 방향). 원형이면 짧은 쪽으로 감. 배열도 받음
    dp = np.asarray(toP) - np.asarray(p)
    ds = np.asarray(toS) - np.asarray(s)
    if G.wrapP:
        dp = (dp + G.numP // 2) % G.numP - G.numP // 2
    if G.wrapS:
        ds = (ds + G.numS // 2) % G.numS - G.numS // 2
    return dp, ds
