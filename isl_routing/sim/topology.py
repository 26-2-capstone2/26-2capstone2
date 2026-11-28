# 위성군(망 구조) 설정 - 가상 격자, Iridium, Starlink를 같은 방식(궤도면 x 궤도면당 위성, 상하좌우 ISL)으로 표현
#
# 좌표: p = 궤도면 번호 (좌/우 = 옆 궤도면으로 가는 링크), s = 궤도 안 위성 번호 (상/하 = 같은 궤도 앞뒤 위성)
#
# [변경] 모든 구조를 직사각형/정사각형 가상 격자로 씀: 끝은 막힘 (원형 연결 없음), 극지방 링크 끊김 없음,
#        링크 지연은 궤도 안(상하) 7, 궤도 사이(좌우) 2 step 고정
#   'iridium', 'starlink'는 그 크기의 가상 격자로 바꿔 씀: iridium -> grid:6x11, starlink -> grid:72x22,
#   'starlink:12x12' -> grid:12x12. 아래 실제 위성군 설명과 거리 계산 코드는 이전 방식 기록용으로만 남김
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
# 흐름 0: 도착은 격자 맨 끝 모서리 (numPlanes-1, satsPerPlane-1), 출발은 에피소드 시드로 무작위 (sim/flows.py)
# 기한과 TTL은 흐름마다 그 흐름의 거리에 6x6과 같은 여유를 더해 정함 (flow_limits, 여유는 P.deadlineMargin, P.ttlMargin)
#   기한 = max(최소 지연, B(DRA) 기본 경로 지연) + 25   (6x6은 둘 다 45 -> 70)
#     실제 위성군은 위도에 따라 옆 궤도 링크 지연이 달라, 좌우 먼저 가는 DRA 기본 경로가 최단 경로보다 길 수 있음
#     -> 혼잡이 없을 때 B도 기한 안에 도착할 수 있게 함
#   TTL = 최소 홉 + 10   (6x6: 10 + 10 = 20)
import math

import numpy as np

EARTH_RADIUS_KM = 6371.0
LIGHT_KM_PER_MS = 299.792458

PRESETS = {
    'iridium': dict(numPlanes=6, satsPerPlane=11, altitudeKm=780.0, inclinationDeg=86.4, planeSpacingDeg=31.6,
                    wrapP=False, wrapS=True, polarLatLimitDeg=60.0),
    'starlink': dict(numPlanes=72, satsPerPlane=22, altitudeKm=550.0, inclinationDeg=53.0, planeSpacingDeg=None,
                     wrapP=True, wrapS=True, polarLatLimitDeg=None),
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
    # 구조 이름으로 P의 망 구조 값을 덮어쓰고, 흐름 0 끝점, 기한과 TTL을 그 구조에 맞게 다시 정함
    base, a, b = parse_name(name)
    if base in PRESETS:   # 실제 위성군 이름은 같은 크기의 가상 격자로 (원형 연결, 극지방 없음)
        a = a or PRESETS[base]['numPlanes']
        b = b or PRESETS[base]['satsPerPlane']
        base = 'grid'
    if base == 'grid':
        P.topology = 'grid'
        P.numPlanes = a or 6
        P.satsPerPlane = b or 6
        P.wrapP = P.wrapS = False
        P.linkDelay = np.array([7, 7, 2, 2])
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
    else:
        raise ValueError(f"구조 이름은 'grid', 'grid:NxM', {list(PRESETS)} (또는 'starlink:NxM'): {name}")
    return update_limits(P)


def update_limits(P):
    # 지금 망 크기에 맞춰 흐름 0 끝점과 기한, TTL 상한을 다시 계산 (격자 크기를 바꾼 뒤에도 부름)
    #   측정 흐름(흐름 0) = (0,0) -> 격자 맨 끝 모서리 (시험 때 고정, 학습 때는 sim/flows.py가 그 거리 근처 쌍 중 무작위)
    #   P.deadline, P.ttlInit = 끝점까지 가장 먼 출발 위성의 기한, TTL (관측 정규화, 홉 보상의 기준값)
    #   흐름마다 실제 기한, TTL은 flow_limits로 그 흐름 거리에 맞춰 정함
    from sim.build_grid import build_grid   # build_grid가 이 파일을 쓰므로 여기서 불러옴
    P.srcSat = np.array([0, 0])
    P.dstSat = np.array([P.numPlanes - 1, P.satsPerPlane - 1])
    G = build_grid(P)
    dst = (int(P.dstSat[0]), int(P.dstSat[1]))
    limits = [flow_limits(P, G, (p, s), dst) for p in range(P.numPlanes) for s in range(P.satsPerPlane) if (p, s) != dst]
    limits = [x for x in limits if x is not None]
    if not limits:
        raise ValueError(f'{P.topology}: 끝점 {dst}으로 가는 경로가 없음')
    delay = G.limitCache[dst][0]
    P.maxFlowDelay = int(delay[np.isfinite(delay)].max())   # D: 끝점까지 가장 먼 위성의 최소 지연 (흐름 1~ 거리 구간의 기준, 6x6: 45)
    P.deadline = max(d for d, _ in limits)
    P.ttlInit = max(t for _, t in limits)
    P.bgTtl = max(getattr(P, 'bgTtl', 20), P.ttlInit)
    if P.topology == 'grid':   # 표시용 이름: 6x6은 'grid', 그 밖의 크기는 'grid:10x10'처럼
        P.topologyName = 'grid' if (P.numPlanes, P.satsPerPlane) == (6, 6) else f'grid:{P.numPlanes}x{P.satsPerPlane}'
    return P


def flow_limits(P, G, src, dst):
    # 흐름 하나의 기한과 TTL: 기한 = max(최소 지연, B 기본 경로 지연) + 여유, TTL = 최소 홉 + 여유 (6x6 (0,0)->(5,5): 70, 20)
    # 경로가 없으면 None
    from routing.route_A import _dist_to
    cache = G.__dict__.setdefault('limitCache', {})
    if dst not in cache:
        cache[dst] = (_dist_to(G, dst), _dist_to(G, dst, hops=True))
    delay, hops = cache[dst][0][src], cache[dst][1][src]
    if not np.isfinite(delay):
        return None
    deadline = int(max(delay, xy_path_delay(G, src, dst))) + getattr(P, 'deadlineMargin', DEADLINE_MARGIN)
    return deadline, int(hops) + getattr(P, 'ttlMargin', TTL_MARGIN)


def xy_path_delay(G, src, dst):
    # 좌우 먼저, 그다음 상하로 가는 기본 경로(DRA가 혼잡이 없을 때 고르는 경로)의 지연. 중간에 링크가 없으면 0
    from sim.bg_traffic import xy_path_links
    try:
        links = xy_path_links(G, np.array(src), np.array(dst))
    except (IndexError, ValueError):
        return 0
    if any(G.nextP[l] < 0 for l in links):
        return 0
    return int(sum(G.linkDelay[l] for l in links))


def sat_lonlat(P):
    # 지도용 위성 위치 [경도, 위도], 순서는 p x 궤도면당 위성 수 + s (한 순간의 배치, latitude_deg와 같은 식)
    # 경도 = 궤도면 p의 승교점 경도(p x 궤도면 간격) + 궤도 위 위치에 따른 경도 차이. 지구 자전은 무시. 가상 격자는 None
    if P.topology == 'grid':
        return None
    inc = math.radians(P.inclinationDeg)
    out = []
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            u = 2 * math.pi * s / P.satsPerPlane
            lat = math.degrees(math.asin(math.sin(inc) * math.sin(u)))
            lon = (p * P.planeSpacingDeg + math.degrees(math.atan2(math.cos(inc) * math.sin(u), math.cos(u))) + 540) % 360 - 180
            out.append([round(lon, 2), round(lat, 2)])
    return out
