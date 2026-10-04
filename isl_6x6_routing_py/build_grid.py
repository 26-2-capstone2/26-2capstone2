# 6x6 Grid 생성 - 위성 좌표, 상/하/좌/우 링크, 링크별 지연·다음 위성을 만듦
#
from types import SimpleNamespace

import numpy as np


def build_grid(P):
    # 6x6 Grid 링크 구조 생성 (Grid 끝은 반대편과 연결하지 않음)
    # 방향 번호: 1 상(s-1), 2 하(s+1), 3 좌(p-1), 4 우(p+1)
    # 파이썬은 좌표를 문서 좌표 그대로(0부터) 사용, 배열 인덱스는 방향 번호 - 1
    G = SimpleNamespace()
    G.stepP = np.array([0, 0, -1, 1])      # 방향별 p 변화량
    G.stepS = np.array([-1, 1, 0, 0])      # 방향별 s 변화량
    G.numLinks = P.numPlanes * P.satsPerPlane * 4
    # 링크 번호 = (p,s,방향) - MATLAB과 같은 순서(열 우선)로 번호를 매김
    G.linkId = np.arange(G.numLinks).reshape((P.numPlanes, P.satsPerPlane, 4), order='F')

    G.hasLink = np.zeros((P.numPlanes, P.satsPerPlane, 4), dtype=bool)   # 그 방향에 링크가 있는지
    G.nextP = np.full(G.numLinks, -1)          # 링크 끝 위성 p (-1: 링크 없음)
    G.nextS = np.full(G.numLinks, -1)          # 링크 끝 위성 s
    G.linkDelay = np.zeros(G.numLinks, dtype=int)   # 링크 지연 (step)
    G.validDirs = [[None] * P.satsPerPlane for _ in range(P.numPlanes)]   # 위성별 갈 수 있는 방향 목록
    G.outLinks = [[None] * P.satsPerPlane for _ in range(P.numPlanes)]    # 위성별 나가는 링크 번호 목록

    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            for d in range(1, 5):
                np_ = p + G.stepP[d - 1]
                ns = s + G.stepS[d - 1]
                if 0 <= np_ < P.numPlanes and 0 <= ns < P.satsPerPlane:
                    G.hasLink[p, s, d - 1] = True
                    l = G.linkId[p, s, d - 1]
                    G.nextP[l] = np_
                    G.nextS[l] = ns
                    G.linkDelay[l] = P.linkDelay[d - 1]
            G.validDirs[p][s] = [d for d in range(1, 5) if G.hasLink[p, s, d - 1]]
            G.outLinks[p][s] = np.array([G.linkId[p, s, d - 1] for d in G.validDirs[p][s]])

    G.srcSat = P.srcSat.copy()
    G.dstSat = P.dstSat.copy()
    return G
