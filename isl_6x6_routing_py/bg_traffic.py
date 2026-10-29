# 배경 트래픽 - 송신 큐 핫스팟 시나리오 뽑기(sample_hotspots), 흐름별 생성 스케줄(ON/OFF), 링크 부하 점검
# 핫스팟 = 위성 하나의 한 방향 송신 큐가 과부하. 1홉짜리 배경 흐름(위성 -> 그 방향 이웃)으로 표현함
import numpy as np


def make_bg_schedule(P):
    # bgCount[f, t] = 흐름 f가 step t에 만드는 패킷 수 (t = 1 ~ simTime, 0열은 안 씀)
    # 배경 전용 난수(bgSeed)를 써서 라우터 동작과 무관하게 항상 같은 시나리오가 나옴
    if len(P.bgFlows) == 0:
        raise RuntimeError('배경 흐름이 비어 있음: 실행 전에 sample_hotspots(P, build_grid(P), 시드)를 호출해야 함')
    rng = np.random.RandomState(P.bgSeed)
    T = P.simTime
    count = np.zeros((len(P.bgFlows), T + 1), dtype=np.int64)
    for f in range(len(P.bgFlows)):
        on = np.zeros(T + 1, dtype=bool)
        state = rng.random_sample() < P.bgOnMean / (P.bgOnMean + P.bgOffMean)   # 시작 상태
        t = 1
        while t <= T:
            length = max(1, int(round(rng.exponential(P.bgOnMean if state else P.bgOffMean))))
            if state:
                on[t:t + length] = True
            t += length
            state = not state
        count[f] = np.where(on, rng.poisson(P.bgOnRate[f], size=T + 1), 0)
    return count


def xy_next_dir(curP, curS, dstP, dstS):
    # 차원 순서(XY) 라우팅: p(좌/우)를 먼저 맞추고 그다음 s(상/하). 도착이면 0
    # 방향 번호: 1 상(s-1), 2 하(s+1), 3 좌(p-1), 4 우(p+1)
    return np.where(dstP > curP, 4,
           np.where(dstP < curP, 3,
           np.where(dstS > curS, 2,
           np.where(dstS < curS, 1, 0))))


def xy_path_links(G, src, dst):
    p, s = int(src[0]), int(src[1])
    links = []
    while (p, s) != (int(dst[0]), int(dst[1])):
        d = int(xy_next_dir(np.array([p]), np.array([s]), np.array([dst[0]]), np.array([dst[1]]))[0])
        links.append(int(G.linkId[p, s, d - 1]))
        p += int(G.stepP[d - 1])
        s += int(G.stepS[d - 1])
    return links


def link_load_report(P, G):
    # 링크별 이론 부하(packets/step)를 계산해 출력. peak > linkCapacity인 링크가 혼잡이 생기는 곳
    duty = P.bgOnMean / (P.bgOnMean + P.bgOffMean)
    avg = np.zeros(G.numLinks)
    peak = np.zeros(G.numLinks)
    for (src, dst), rate in zip(P.bgFlows, P.bgOnRate):
        for l in xy_path_links(G, src, dst):
            avg[l] += rate * duty
            peak[l] += rate
    shape = (P.numPlanes, P.satsPerPlane, 4)
    for l in np.flatnonzero(peak > P.linkCapacity):
        p, s, d = np.unravel_index(l, shape, order='F')
        print(f'혼잡 링크 (p={p}, s={s}, 방향={d + 1}): 최대 {peak[l]:.1f}, 평균 {avg[l]:.1f} packets/step')
    return avg, peak


def sample_hotspots(P, G, seed, maxTry=500):
    # 송신 큐 핫스팟(위성, 방향)을 무작위로 뽑아 P.bgFlows / P.bgOnRate / P.bgSeed를 채움
    #   같은 시드면 항상 같은 시나리오. 한 번 실행(에피소드)을 시작하기 전에 한 번만 호출
    #   반환: 뽑힌 핫스팟 목록 [(p, s, 방향, 다음 p, 다음 s, 주 흐름과 관련 있는 큐인지)], 세기 목록(packets/step)
    rng = np.random.RandomState(seed)
    src = (int(P.srcSat[0]), int(P.srcSat[1]))
    dst = (int(P.dstSat[0]), int(P.dstSat[1]))
    pLo, pHi = sorted((src[0], dst[0]))
    sLo, sHi = sorted((src[1], dst[1]))
    # 후보: 격자의 모든 (위성, 방향). 도착 위성의 큐는 제외
    cand, weight = [], []
    for p in range(P.numPlanes):
        for s in range(P.satsPerPlane):
            if (p, s) == dst:
                continue
            for d in G.validDirs[p][s]:
                np_, ns_ = p + int(G.stepP[d - 1]), s + int(G.stepS[d - 1])
                # 목적지에 가까워지는 방향이고 출발-도착 사각형 안이면 '주 흐름과 관련 있는' 큐
                closer = abs(dst[0] - np_) + abs(dst[1] - ns_) < abs(dst[0] - p) + abs(dst[1] - s)
                inBox = pLo <= p <= pHi and sLo <= s <= sHi
                rel = closer and inBox
                cand.append((p, s, d, np_, ns_, rel))
                weight.append(P.bgRelWeight if rel else 1.0)
    weight = np.array(weight, dtype=float) / np.sum(weight)
    for _ in range(maxTry):
        K = rng.randint(P.bgNumMin, P.bgNumMax + 1)
        idx = rng.choice(len(cand), size=K, replace=False, p=weight)
        rates = [float(x) * P.linkCapacity for x in rng.uniform(P.bgLoadMin, P.bgLoadMax, size=K)]
        picked = [cand[i] for i in idx]
        nRel = sum(c[5] for c in picked)
        # 큐를 가득 채워 막는 수준(부하 >= bgBlockLoad)인 핫스팟은 '막힌 포트'로 보고, 그걸 빼도 도착할 길이 있는지 확인
        blocked = {(c[0], c[1], c[2]) for c, r in zip(picked, rates) if r >= P.bgBlockLoad * P.linkCapacity}
        if nRel >= P.bgMinRelevant and path_exists(P, G, src, dst, blocked):
            P.bgFlows = [((c[0], c[1]), (c[3], c[4])) for c in picked]
            P.bgOnRate = rates
            P.bgSeed = int(seed) + 100000          # ON/OFF 난수는 시나리오 뽑기와 다른 난수열을 쓰도록 시드를 벌려 둠
            return picked, rates
    raise RuntimeError('조건을 만족하는 시나리오를 못 뽑음: 개수/부하/bgMinRelevant 범위를 완화하세요')


def path_exists(P, G, src, dst, blocked):
    # 상하좌우 모든 방향(뒤로 돌아가는 것 포함)을 쓸 수 있을 때, 막힌 큐를 제외하고 도착할 수 있는가
    seen, stack = {src}, [src]
    while stack:
        p, s = stack.pop()
        if (p, s) == dst:
            return True
        for d in G.validDirs[p][s]:
            if (p, s, d) in blocked:
                continue
            q = (p + int(G.stepP[d - 1]), s + int(G.stepS[d - 1]))
            if q not in seen:
                seen.add(q)
                stack.append(q)
    return False


def describe_hotspots(picked, rates, P):
    # 사람이 읽기 쉬운 한 줄 설명 (방향 번호: 1 상, 2 하, 3 좌, 4 우)
    name = {1: '상', 2: '하', 3: '좌', 4: '우'}
    return ', '.join(f'({c[0]},{c[1]}){name[c[2]]} 부하 {r / P.linkCapacity:.1f}' for c, r in zip(picked, rates))
