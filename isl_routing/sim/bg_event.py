# 배경 트래픽 (혼잡 사건 방식, P.bgMode = 'event') - 기본 부하 위에 지역 핫스팟이 무작위로 생겼다 사라짐
#
# 기존 방식(bg_traffic.py, 'hotspot'): 에피소드 시작에 핫스팟 위치를 한 번 뽑고 끝까지 고정, 켜짐/꺼짐만 반복
# 이 방식('event'), 선행 연구 참고: DTAR (기본 트래픽 + 무작위 지역 급증), Back-Pressure 부하 분산 (버스트 평균 1초)
#   1. 기본 부하: 모든 링크에 에피소드 내내 링크 용량의 P.bgBaseMin ~ P.bgBaseMax배 (링크마다 에피소드 시작에 정함)
#   2. 지역 핫스팟: 포아송 과정으로 발생 (평균 간격 P.evIntervalMean step)
#      위치: 사건마다 중심 위성을 새로 뽑음. 주 흐름이 지나는 지역(출발 -> 도착 직선에서 P.evCorridor칸 이내)은 P.bgRelWeight배 더 잘 뽑힘
#      범위: 중심 위성의 송신 링크에 P.evLoadMin ~ P.evLoadMax배, 이웃 위성의 송신 링크에 그 P.evNbrRatio배를 더함
#      지속: 지수분포 (평균 P.evDurationMean step), 끝나면 큐에 남은 패킷은 그대로 비워짐
#      위치, 세기, 시점, 지속이 모두 무작위라 특정 혼잡 패턴을 외울 수 없음
#      안전: 그 순간의 부하 합이 링크 용량의 P.evSafeLoad배 이상(넘치는 링크)인 링크를 모두 빼고도 출발 -> 도착 길이 있어야 함
#            없으면 위치를 다시 뽑고, maxTry번 안에 못 찾으면 그 핫스팟은 건너뜀 (라우팅으로 피할 수 없는 손실을 만들지 않기 위해)
# 혼잡 단계별 발생 간격, 지속 시간은 config_isl.py의 EVENT_LEVELS
#
# 시뮬레이터(run_isl_sim)가 쓰는 모양은 기존과 같음: 흐름 1개 = 1홉 배경 흐름 (P.bgFlows, P.bgOnRate)
#   P.bgEvents: 흐름별 (시작 step, 끝 step) - 기본 부하는 (1, simTime)
import numpy as np

from sim.bg_traffic import path_exists


def _links(G, p, s):
    # 위성 (p, s)의 송신 링크 [(p, s, 방향, 다음 p, 다음 s)]
    return [(p, s, d, int(G.nbrP[p, s, d - 1]), int(G.nbrS[p, s, d - 1])) for d in G.validDirs[p][s]]


def sample_events(P, G, seed, maxTry=500):
    # 에피소드 하나의 기본 부하와 지역 핫스팟을 뽑아 P.bgFlows / P.bgOnRate / P.bgEvents / P.bgSeed를 채움
    # 반환: 흐름 목록 [(p, s, 방향, 다음 p, 다음 s, 핫스팟이면 1)], 세기 목록 (sample_hotspots와 같은 모양)
    rng = np.random.RandomState(seed)
    src = (int(P.srcSat[0]), int(P.srcSat[1]))
    dst = (int(P.dstSat[0]), int(P.dstSat[1]))
    mainFlows = getattr(P, 'mainFlows', None) or [(src, dst)]   # 주 흐름이 여러 개면 모든 흐름에 대해 지역 가중치와 안전장치를 적용
    cap = P.linkCapacity
    flows, rates, events = [], [], []

    # 1. 기본 부하
    base = {}
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            for c in _links(G, p, s):
                r = float(rng.uniform(P.bgBaseMin, P.bgBaseMax)) * cap
                base[c[:3]] = r
                flows.append(c + (0,)); rates.append(r); events.append((1, P.simTime))

    # 2. 지역 핫스팟
    dsts = {d for _, d in mainFlows}
    centers = [(p, s) for p in range(P.numPlanes) for s in range(P.satsPerPlane) if (p, s) not in dsts]

    def lineDist(p, s):   # 가장 가까운 주 흐름의 출발 -> 도착 직선까지 거리 (칸)
        out = np.inf
        for a, b in mainFlows:
            dP, dS = b[0] - a[0], b[1] - a[1]
            out = min(out, abs(dS * (p - a[0]) - dP * (s - a[1])) / max(np.hypot(dP, dS), 1e-9))
        return out
    cw = np.array([P.bgRelWeight if lineDist(p, s) <= P.evCorridor else 1.0 for p, s in centers])
    cw /= cw.sum()
    hot = []   # (시작, 끝, 링크, 추가 세기)
    t = 0.0
    while True:
        t += rng.exponential(P.evIntervalMean)
        start = int(round(t))
        if start > P.simTime:
            break
        end = min(P.simTime, start + max(1, int(round(rng.exponential(P.evDurationMean)))))
        for _ in range(maxTry):
            cp, cs = centers[rng.choice(len(centers), p=cw)]
            links = _links(G, cp, cs)
            add = [float(rng.uniform(P.evLoadMin, P.evLoadMax)) * cap for _ in links]
            for _, _, _, np_, ns_ in list(links):          # 이웃 위성의 송신 링크도 약하게 함께 막힘 (지역 혼잡)
                for c in _links(G, np_, ns_):
                    links.append(c)
                    add.append(float(rng.uniform(P.evLoadMin, P.evLoadMax)) * P.evNbrRatio * cap)
            load = dict(base)                          # 이 순간 링크별 부하 합
            for a, b, c, r in hot:
                if a <= start <= b:
                    load[c[:3]] += r
            for c, r in zip(links, add):
                load[c[:3]] += r
            blocked = {k for k, v in load.items() if v >= P.evSafeLoad * cap}
            if all(path_exists(P, G, a, b, blocked) for a, b in mainFlows):   # 모든 주 흐름에 피할 길이 남아야 함
                break
        else:
            continue                                   # 피할 길을 남기는 위치가 없으면 이 핫스팟은 건너뜀
        for c, r in zip(links, add):
            hot.append((start, end, c, r))
            flows.append(c + (1,)); rates.append(r); events.append((start, end))

    P.bgFlows = [((c[0], c[1]), (c[3], c[4])) for c in flows]
    P.bgOnRate = rates
    P.bgEvents = events
    P.bgSeed = int(seed) + 100000          # 패킷 생성 난수는 위치 뽑기와 다른 난수열
    return flows, rates


def make_event_schedule(P):
    # bgCount[f, t] = 흐름 f가 step t에 만드는 배경 패킷 수 (켜져 있는 [시작, 끝] 동안 포아송)
    rng = np.random.RandomState(P.bgSeed)
    count = np.zeros((len(P.bgFlows), P.simTime + 1), dtype=np.int64)
    for f, (a, b) in enumerate(P.bgEvents):
        a = max(a, 1)
        count[f, a:b + 1] = rng.poisson(P.bgOnRate[f], size=b - a + 1)
    return count
