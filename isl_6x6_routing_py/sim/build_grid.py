# 6x6 Grid 생성 - 위성 좌표, 상/하/좌/우 링크, 링크별 지연, 다음 위성을 만듦
#
# 흐름: (1) 방향 정의 -> (2) 링크 번호표 -> (3) 빈 표 준비 -> (4) 위성 x 방향마다 링크 채우기 -> (5) 출발/도착 저장
# 결과 G는 run_isl_sim, route_A, route_B, node_log가 "이 위성에서 이 방향으로 가면 어디로, 몇 step?"을 찾을 때 씀
from types import SimpleNamespace

import numpy as np


def build_grid(P):
    # 6x6 Grid 링크 구조 생성 (Grid 끝은 반대편과 연결하지 않음)
    # 방향 번호: 1 상(s-1), 2 하(s+1), 3 좌(p-1), 4 우(p+1)
    G = SimpleNamespace()

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

    # (4) 위성 36개 x 방향 4개를 하나씩 보면서 링크 채우기
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            for d in range(1, 5):
                np_ = p + G.stepP[d - 1]   # 이 방향으로 갔을 때 도착하는 위성 좌표
                ns = s + G.stepS[d - 1]
                if 0 <= np_ < P.numPlanes and 0 <= ns < P.satsPerPlane:   # Grid 안이면 링크 있음 (밖이면 건너뜀)
                    G.hasLink[p, s, d - 1] = True
                    l = G.linkId[p, s, d - 1]
                    G.nextP[l] = np_               # 링크 l을 타면 도착하는 위성
                    G.nextS[l] = ns
                    G.linkDelay[l] = P.linkDelay[d - 1]   # 상/하 7 step, 좌/우 2 step (config_isl)
            # 이 위성에서 갈 수 있는 방향과 그 링크 번호 (모서리 2개, 가장자리 3개, 안쪽 4개)
            G.validDirs[p][s] = [d for d in range(1, 5) if G.hasLink[p, s, d - 1]]
            G.outLinks[p][s] = np.array([G.linkId[p, s, d - 1] for d in G.validDirs[p][s]])

    # (5) 출발/도착 위성 (route_A, route_B가 목적지 방향을 계산할 때 사용)
    G.srcSat = P.srcSat.copy()
    G.dstSat = P.dstSat.copy()
    return G
