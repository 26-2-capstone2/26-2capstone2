# 위성군(망 구조) 설정 - 가상 격자, Iridium, Starlink를 같은 방식(궤도면 x 궤도면당 위성, 상하좌우 ISL)으로 표현
#
# 좌표: p = 궤도면 번호 (좌/우 = 옆 궤도면으로 가는 링크), s = 궤도 안 위성 번호 (상/하 = 같은 궤도 앞뒤 위성)
#
# 구조 이름 (apply_topology의 name)
#   'grid'      가상 격자. 크기 자유 (예: 'grid:8x8'), 끝은 막힘, 링크 지연 고정 (상하 7, 좌우 2 step)
#   'iridium'   6 x 11, 극궤도 (고도 780 km, 경사각 86.4도)
#               같은 궤도는 원형으로 이어짐, 1번과 6번 궤도면 사이(seam)는 반대 방향으로 돌아 링크 없음
#               극지방(위도 60도 이상)에서는 옆 궤도 링크가 꺼짐
#   'starlink'  72 x 22, 고도 550 km, 경사각 53도, 같은 궤도와 옆 궤도 모두 원형 (+Grid)
#               축소판은 'starlink:12x12'처럼 크기를 줌 (궤도면 간격, 위성 간격은 크기에 맞춰 다시 계산)
#
# 실제 위성군 링크 지연은 위성 사이 직선 거리 ÷ 빛의 속도 (1 step = 1 ms, 1 step 단위로 반올림, 최소 1)
#   같은 궤도: 2R sin(pi / 궤도면당 위성 수)
#   옆 궤도:   2R sin(궤도면 간격 / 2) x cos(위도)  (적도에서 가장 멀고 극으로 갈수록 가까워지는 근사)
#   위성 s의 위도 = asin(sin(경사각) x sin(2 pi s / 궤도면당 위성 수)), 한 순간(정지 상태)의 배치
# 기한과 TTL은 6x6과 같은 여유를 더해 정함
#   기한 = max(최소 지연, B(DRA) 기본 경로 지연) + 25   (6x6은 둘 다 45 -> 70)
#     실제 위성군은 위도에 따라 옆 궤도 링크 지연이 달라, 좌우 먼저 가는 DRA 기본 경로가 최단 경로보다 길 수 있음
#     -> 혼잡이 없을 때 B도 기한 안에 도착할 수 있게 함
#   TTL = 최소 홉 + 10   (6x6: 10 + 10 = 20)
import heapq
import math

import numpy as np

EARTH_RADIUS_KM = 6371.0
LIGHT_KM_PER_MS = 299.792458

PRESETS = {
    'iridium': dict(numPlanes=6, satsPerPlane=11, altitudeKm=780.0, inclinationDeg=86.4, planeSpacingDeg=31.6,
                    wrapP=False, wrapS=True, polarLatLimitDeg=60.0, src=(0, 0), dst=(5, 5)),
    'starlink': dict(numPlanes=72, satsPerPlane=22, altitudeKm=550.0, inclinationDeg=53.0, planeSpacingDeg=None,
                     wrapP=True, wrapS=True, polarLatLimitDeg=None, src=(0, 0), dst=None),
}
DEADLINE_MARGIN = 25   # 6x6: 최소 지연 45 + 25 = 기한 70
TTL_MARGIN = 10        # 6x6: 최소 홉 10 + 10 = TTL 20


def parse_name(name):
    # 'grid:8x8' -> ('grid', 8, 8), 'starlink' -> ('starlink', None, None)
    base, _, size = name.partition(':')
    if size:
        a, b = size.lower().split('x')
        return base, int(a), int(b)
    return base, None, None


def latitude_deg(P, s):
    u = 2 * math.pi * s / P.satsPerPlane
    return math.degrees(math.asin(math.sin(math.radians(P.inclinationDeg)) * math.sin(u)))


def link_enabled(P, p, s, d):
    # 실제 위성군에서 그 링크가 켜져 있는가 (극지방 옆 궤도 링크 꺼짐). d: 1 상, 2 하, 3 좌, 4 우
    if P.topology == 'grid' or d in (1, 2) or P.polarLatLimitDeg is None:
        return True
    return abs(latitude_deg(P, s)) < P.polarLatLimitDeg


def link_delay_steps(P, s, d):
    # 링크 지연 (step). 가상 격자는 방향별 고정값, 실제 위성군은 거리로 계산
    if P.topology == 'grid':
        return int(P.linkDelay[d - 1])
    r = EARTH_RADIUS_KM + P.altitudeKm
    if d in (1, 2):
        km = 2 * r * math.sin(math.pi / P.satsPerPlane)
    else:
        spacing = math.radians(P.planeSpacingDeg)
        km = 2 * r * math.sin(spacing / 2) * math.cos(math.radians(latitude_deg(P, s)))
    return max(1, int(round(km / LIGHT_KM_PER_MS)))


def apply_topology(P, name='grid'):
    # 구조 이름으로 P의 망 구조 값을 덮어쓰고, 기한과 TTL을 그 구조에 맞게 다시 정함
    from sim.build_grid import build_grid   # build_grid가 이 파일을 쓰므로 여기서 불러옴
    base, a, b = parse_name(name)
    if base == 'grid':
        P.topology = 'grid'
        P.numPlanes = a or 6
        P.satsPerPlane = b or 6
        P.wrapP = P.wrapS = False
        P.linkDelay = np.array([7, 7, 2, 2])
        P.srcSat = np.array([0, 0])
        P.dstSat = np.array([P.numPlanes - 1, P.satsPerPlane - 1])
    elif base in PRESETS:
        c = PRESETS[base]
        P.topology = base
        P.numPlanes = a or c['numPlanes']
        P.satsPerPlane = b or c['satsPerPlane']
        P.altitudeKm = c['altitudeKm']
        P.inclinationDeg = c['inclinationDeg']
        P.planeSpacingDeg = c['planeSpacingDeg'] or 360.0 / P.numPlanes
        P.wrapP, P.wrapS = c['wrapP'], c['wrapS']
        P.polarLatLimitDeg = c['polarLatLimitDeg']
        P.srcSat = np.array(c['src'])
        dst = c['dst'] or (P.numPlanes // 2, P.satsPerPlane // 2)    # 원형 구조는 가장 먼 위성 쪽
        P.dstSat = np.array([min(dst[0], P.numPlanes - 1), min(dst[1], P.satsPerPlane - 1)])
    else:
        raise ValueError(f"구조 이름은 'grid', 'grid:NxM', {list(PRESETS)} (또는 'starlink:NxM'): {name}")

    G = build_grid(P)
    minDelay, minHops = shortest_from_src(G)
    if not np.isfinite(minDelay):
        raise ValueError(f'{name}: 출발 위성에서 도착 위성으로 가는 경로가 없음')
    P.deadline = int(max(minDelay, xy_path_delay(G))) + DEADLINE_MARGIN
    P.ttlInit = int(minHops) + TTL_MARGIN
    P.bgTtl = max(getattr(P, 'bgTtl', 20), P.ttlInit)
    return P


def xy_path_delay(G):
    # 좌우 먼저, 그다음 상하로 가는 기본 경로(DRA가 혼잡이 없을 때 고르는 경로)의 지연. 중간에 링크가 없으면 0
    from sim.bg_traffic import xy_path_links
    try:
        links = xy_path_links(G, G.srcSat, G.dstSat)
    except (IndexError, ValueError):
        return 0
    if any(G.nextP[l] < 0 for l in links):
        return 0
    return int(sum(G.linkDelay[l] for l in links))


def shortest_from_src(G):
    # 출발 위성 -> 도착 위성 최소 지연 (step)과 최소 홉 수
    def search(weight):
        best = {(int(G.srcSat[0]), int(G.srcSat[1])): 0}
        heap = [(0, int(G.srcSat[0]), int(G.srcSat[1]))]
        while heap:
            c, p, s = heapq.heappop(heap)
            if (p, s) == (int(G.dstSat[0]), int(G.dstSat[1])):
                return c
            if c > best[(p, s)]:
                continue
            for d in G.validDirs[p][s]:
                l = G.linkId[p, s, d - 1]
                q = (int(G.nextP[l]), int(G.nextS[l]))
                nc = c + weight(l)
                if nc < best.get(q, np.inf):
                    best[q] = nc
                    heapq.heappush(heap, (nc, q[0], q[1]))
        return np.inf
    return search(lambda l: int(G.linkDelay[l])), search(lambda l: 1)
