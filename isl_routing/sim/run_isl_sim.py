# 시뮬레이션 1회 실행 - 매 step(1 ms) 도착→확인→생성→라우팅→전송을 반복하고 결정 기록을 남김
#
import math
import warnings
from types import SimpleNamespace

import numpy as np

from sim.build_grid import build_grid, displacement
from routing.route_A import route_A
from routing.route_B import route_B
from routing.route_C import route_C, STATE as C_STATE
from sim.bg_traffic import make_bg_schedule, xy_next_dir
from sim.link_history import LinkHistory
from sim.node_log import NodeLog

# 라우팅 알고리즘 (config_isl.py의 P.routeName으로 선택)
#   ROUTE_LABELS: 그래프/애니메이션에 쓰는 이름 (첫 글자 = 짧은 이름, plot_analysis가 [0]으로 씀)
#   강화학습 라우터를 추가할 때는 아래 두 표에 한 줄씩 넣으면 됨 (입출력은 route_B와 같게)
ROUTE_FUNCS = {'routeA': route_A, 'routeB': route_B, 'routeC': route_C}
ROUTE_LABELS = {'routeA': 'A 정적 최단 경로', 'routeB': 'B DRA', 'routeC': 'C 강화학습'}


def run_isl_sim(P, genRate, epsilon, randomSeed, recordAnim):
    # 2D Grid ISL 시뮬레이션 1회 실행 (매 step = 1 ms)
    # genRate: 1초마다 생성하는 패킷 수 (일정 간격), epsilon: 무작위 선택 확률 ε
    # recordAnim: True면 애니메이션용 큐/전송 상태 기록
    #
    # 패킷 상태 status: 0 진행 중, 1 기한 내 도착, 2 목적지 기한 초과,
    #                   3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료
    # 패킷 id(packet_id)는 0부터 시작 (MATLAB 기록 파일과 같은 번호)

    rng = np.random.RandomState(randomSeed)   # MATLAB rng(seed, 'twister')와 같은 난수열
    G = build_grid(P)
    numLinks = G.numLinks
    queueMax = P.queueMax

    # 링크별 큐 (원형 버퍼, 패킷 id 저장)
    queueBuf = np.zeros((numLinks, queueMax), dtype=np.int64)
    queueHead = np.zeros(numLinks, dtype=np.int64)
    queueLen = np.zeros(numLinks, dtype=np.int64)

    # 패킷 정보
    stepsPerSec = round(1 / P.stepTime)

    def numNew(t):   # t step에 생성할 개수 (t=1에 첫 패킷)
        return (t - 1) * genRate // stepsPerSec - (t - 2) * genRate // stepsPerSec

    maxPackets = (P.simTime - 1) * genRate // stepsPerSec + 1
    bgOn = bool(getattr(P, 'bgEnable', False))
    bgBase = maxPackets                       # 배경 패킷 id는 maxPackets 이상
    bgPool = P.bgPoolSize if bgOn else 0
    total = maxPackets + bgPool
    genTime = np.zeros(total, dtype=np.int64)
    ttl = np.zeros(total, dtype=np.int64)
    hops = np.zeros(total, dtype=np.int64)
    curP = np.zeros(total, dtype=np.int64)
    curS = np.zeros(total, dtype=np.int64)
    status = np.zeros(total, dtype=np.int64)
    endTime = np.zeros(total, dtype=np.int64)
    onLink = np.full(total, -1, dtype=np.int64)
    statusCount = np.zeros(5, dtype=np.int64)
    dstP = np.zeros(total, dtype=np.int64)    # 배경 패킷의 목적지
    dstS = np.zeros(total, dtype=np.int64)
    bgFree = list(range(total - 1, bgBase - 1, -1))
    bgStat = dict(generated=0, delivered=0, overflow=0, ttlExpired=0, srcDrop=0)
    if bgOn:
        bgCount = make_bg_schedule(P)
        bgFlowSP = np.array([f[0][0] for f in P.bgFlows], dtype=np.int64)   # 흐름별 출발, 도착 위성 (배열로 한꺼번에 생성)
        bgFlowSS = np.array([f[0][1] for f in P.bgFlows], dtype=np.int64)
        bgFlowDP = np.array([f[1][0] for f in P.bgFlows], dtype=np.int64)
        bgFlowDS = np.array([f[1][1] for f in P.bgFlows], dtype=np.int64)
    linkSent = np.zeros(numLinks, dtype=np.int64)
    hist = LinkHistory(numLinks)   # 링크별 최근 큐 길이, 마지막 넘침 시각 (route_C 관측용)

    # 라우팅 함수 선택
    routeName = getattr(P, 'routeName', 'routeB')
    if not isinstance(routeName, str) or routeName not in ROUTE_FUNCS:
        raise ValueError(f'P.routeName은 {list(ROUTE_FUNCS)} 중 하나여야 함 (지금: {routeName!r})')
    route = ROUTE_FUNCS[routeName]
    collector = C_STATE.collector if routeName == 'routeC' else None   # 강화학습 경험 연결 장치 (학습 때만)
    stepHook = getattr(P, 'stepHook', None)   # 웹 화면용: 매 step 끝에 상태를 넘겨받는 함수 (없으면 아무 일도 안 함)

    # 노드 기록 (node_log.py). 패킷 id < maxPackets 이면 주 흐름, 이상이면 배경
    nlog = NodeLog(P, G, maxPackets) if getattr(P, 'nodeLogEnable', False) else None

    # 도착 예정 패킷 (도착 step별 칸, 원형)
    numSlots = int(G.maxLinkDelay) + P.processingDelay + 1   # 가장 긴 링크 지연까지 (실제 위성군은 링크마다 다름)
    arrivalSlot = [[] for _ in range(numSlots)]

    # 결정 기록 (라우팅 결정 1번 = 1줄)
    decisionLog = np.zeros((max(maxPackets, 1) * 12, 24))
    numDecisions = 0

    maxSteps = P.simTime + P.maxDrainTime
    timeline = np.zeros((maxSteps, 6), dtype=np.int64)   # 누적: 생성, 기한 내 도착, 목적지 기한 초과, 중간 기한 초과, 오버플로, TTL 만료
    if recordAnim:
        animSteps = min(P.animDuration, maxSteps)
        animQueue = np.zeros((numLinks, animSteps), dtype=np.uint8)      # step별 링크 큐 길이
        animInFlight = np.zeros((numLinks, animSteps), dtype=np.uint16)  # step별 링크 위 전송 중 패킷 수

    numPackets = 0
    t = 0
    while True:
        t += 1
        if t > maxSteps:
            warnings.warn('maxDrainTime 안에 모든 패킷이 끝나지 않음')
            t = maxSteps
            break

        # 1. 도착 처리: 홉 수 +1, TTL -1
        slot = t % numSlots
        arrived = np.array(sorted(arrivalSlot[slot]), dtype=np.int64)
        arrivalSlot[slot] = []
        onLink[arrived] = -1
        hops[arrived] += 1
        ttl[arrived] -= 1
        bgArrived = arrived[arrived >= bgBase]
        arrived = arrived[arrived < bgBase]

        # 2. 목적지 확인
        atDst = (curP[arrived] == G.dstSat[0]) & (curS[arrived] == G.dstSat[1])
        age = t - genTime[arrived]
        onTimeIds = arrived[atDst & (age <= P.deadline)]
        status[onTimeIds] = 1
        endTime[onTimeIds] = t
        lateIds = arrived[atDst & (age > P.deadline)]
        status[lateIds] = 2
        endTime[lateIds] = t

        # 3. 중간 위성 확인: 기한 초과 -> TTL 만료
        inTransit = arrived[~atDst]
        overDeadline = t - genTime[inTransit] > P.deadline
        status[inTransit[overDeadline]] = 3
        endTime[inTransit[overDeadline]] = t
        lateMidIds = inTransit[overDeadline]
        inTransit = inTransit[~overDeadline]
        ttlExpired = ttl[inTransit] <= 0
        status[inTransit[ttlExpired]] = 5
        endTime[inTransit[ttlExpired]] = t
        ttlIds = inTransit[ttlExpired]
        inTransit = inTransit[~ttlExpired]
        statusCount += [len(onTimeIds), len(lateIds), int(overDeadline.sum()), 0, int(ttlExpired.sum())]
        if nlog is not None:   # 주 흐름 패킷이 끝난 노드 (= 방금 도착한 위성)
            nlog.add(4, nlog.node(curP[onTimeIds], curS[onTimeIds]))
            nlog.add(5, nlog.node(curP[lateIds], curS[lateIds]))
            nlog.add(2, nlog.node(curP[lateMidIds], curS[lateMidIds]))
            nlog.add(3, nlog.node(curP[ttlIds], curS[ttlIds]))
        if collector is not None:
            collector.on_end(arrived[status[arrived] != 0], status)   # 이번 step에 끝난 패킷 (강화학습 보상)

        # 3-B. 배경 패킷 도착 처리
        bgRoute = np.zeros(0, dtype=np.int64)
        if len(bgArrived):
            bgAtDst = (curP[bgArrived] == dstP[bgArrived]) & (curS[bgArrived] == dstS[bgArrived])
            bgDone = bgArrived[bgAtDst]
            bgRest = bgArrived[~bgAtDst]
            bgExpired = bgRest[ttl[bgRest] <= 0]
            bgRoute = bgRest[ttl[bgRest] > 0]
            bgStat['delivered'] += len(bgDone)
            bgStat['ttlExpired'] += len(bgExpired)
            bgFree.extend(bgDone.tolist())
            bgFree.extend(bgExpired.tolist())

        # 4. 패킷 생성
        newIds = np.zeros(0, dtype=np.int64)
        if t <= P.simTime and numNew(t) > 0:
            newIds = np.arange(numPackets, numPackets + numNew(t))
            numPackets += numNew(t)
            genTime[newIds] = t
            ttl[newIds] = P.ttlInit
            hops[newIds] = 0
            curP[newIds] = G.srcSat[0]
            curS[newIds] = G.srcSat[1]

                # 4-B. 배경 패킷 생성
        #   흐름 순서대로 빈 id를 받음 (빈 id가 모자라면 뒤쪽 흐름부터 못 만듦 = srcDrop)
        bgNew = []
        if bgOn and t <= P.simTime:
            flows = np.flatnonzero(bgCount[:, t])
            if len(flows):
                perPkt = np.repeat(flows, bgCount[flows, t])   # 패킷마다 어느 흐름인지
                k = min(len(perPkt), len(bgFree))
                bgStat['generated'] += len(perPkt)
                bgStat['srcDrop'] += len(perPkt) - k
                if k > 0:
                    ids = np.array(bgFree[:-k - 1:-1], dtype=np.int64)   # list.pop()을 k번 한 것과 같은 순서
                    del bgFree[-k:]
                    f = perPkt[:k]
                    genTime[ids] = t
                    ttl[ids] = P.bgTtl
                    hops[ids] = 0
                    curP[ids] = bgFlowSP[f]
                    curS[ids] = bgFlowSS[f]
                    dstP[ids] = bgFlowDP[f]
                    dstS[ids] = bgFlowDS[f]
                    onLink[ids] = -1
                    bgNew.append(ids)

        # 4-C. 배경 패킷 큐 진입 (XY 고정 경로)
        bgIds = np.concatenate([bgRoute] + bgNew)
        if len(bgIds):
            bp = curP[bgIds]
            bs = curS[bgIds]
            bd = xy_next_dir(bp, bs, dstP[bgIds], dstS[bgIds], G)
            bl = G.linkId[bp, bs, bd - 1]
            order = np.argsort(bl, kind='stable')
            bgIds = bgIds[order]
            bl = bl[order]
            #   링크별로 큐 빈자리만큼 앞에서부터 넣고 나머지는 오버플로 (링크마다 반복하지 않고 한꺼번에)
            first = np.r_[0, np.flatnonzero(np.diff(bl)) + 1]                 # 링크 묶음의 시작 위치
            rank = np.arange(len(bl)) - np.repeat(first, np.diff(np.r_[first, len(bl)]))   # 묶음 안 순번
            ok = rank < (queueMax - queueLen[bl])
            if ok.any():
                okL = bl[ok]
                queueBuf[okL, (queueHead[okL] + queueLen[okL] + rank[ok]) % queueMax] = bgIds[ok]
                queueLen += np.bincount(okL, minlength=numLinks)
            if not ok.all():
                lost = bgIds[~ok]
                lostL = bl[~ok]
                bgStat['overflow'] += len(lost)
                for link in np.unique(lostL):
                    hist.drop(int(link), t)
                if nlog is not None:
                    nlog.add(1, nlog.linkNode[lostL])
                bgFree.extend(lost.tolist())

        # 5. 라우팅 결정 (도착 패킷 -> 생성 패킷 순)
        toRoute = np.concatenate([inTransit, newIds])
        for packet_id in toRoute:
            p = int(curP[packet_id])
            s = int(curS[packet_id])
            nextDir, choiceType, L, N = route(p, s, queueLen, G, P, t=t, remDeadline=P.deadline - (t - genTime[packet_id]),
                                              ttl=int(ttl[packet_id]), hops=int(hops[packet_id]), hist=hist)   # 패킷 정보와 링크 기록은 route_C만 씀
            if epsilon > 0 and rng.random_sample() < epsilon:
                dirs = G.validDirs[p][s]
                nextDir = dirs[math.ceil(rng.random_sample() * len(dirs)) - 1]
                choiceType = 4   # 무작위

            link = G.linkId[p, s, nextDir - 1]
            enqueued = queueLen[link] < queueMax
            qAtLink = int(queueLen[link])   # 넣기 전 큐 길이 (강화학습 홉 보상용)

            qNow = [-1] * 4
            for d, l in zip(G.validDirs[p][s], G.outLinks[p][s]):
                qNow[d - 1] = queueLen[l]

            if numDecisions >= decisionLog.shape[0]:
                decisionLog = np.vstack([decisionLog, np.zeros_like(decisionLog)])
            decisionLog[numDecisions, :] = [t, packet_id, hops[packet_id], p, s, *qNow, *L, *N,
                                            *displacement(G, p, s, G.dstSat[0], G.dstSat[1]),
                                            P.deadline - (t - genTime[packet_id]), ttl[packet_id],
                                            nextDir, choiceType, enqueued]
            numDecisions += 1

            if enqueued:
                pos = (queueHead[link] + queueLen[link]) % queueMax
                queueBuf[link, pos] = packet_id
                queueLen[link] += 1
            else:
                status[packet_id] = 4   # 큐 오버플로
                endTime[packet_id] = t
                statusCount[3] += 1
                hist.drop(link, t)
                if nlog is not None:
                    nlog.add(0, [nlog.node(p, s)])
            if collector is not None and choiceType != 4:   # route_C 학습: 방금 결정을 경험으로 연결 (ε 무작위 결정은 제외)
                collector.on_decision(int(packet_id), C_STATE.last, qAtLink, enqueued, int(G.linkDelay[link]))

        if nlog is not None:
            nlog.peak(queueLen)   # 라우팅 후 전송 전 (큐가 가장 찬 순간)

        # 6. 전송: 링크마다 큐 앞쪽 최대 linkCapacity개
        #   링크마다 반복하지 않고 한꺼번에 처리 (패킷 순서는 링크 번호순, 링크 안에서는 큐 앞쪽부터)
        sendL = np.flatnonzero(queueLen > 0)
        if len(sendL):
            sendN = np.minimum(queueLen[sendL], P.linkCapacity)
            pktL = np.repeat(sendL, sendN)                                      # 패킷마다 보내는 링크
            rank = np.arange(len(pktL)) - np.repeat(np.cumsum(sendN) - sendN, sendN)
            ids = queueBuf[pktL, (queueHead[pktL] + rank) % queueMax]
            queueHead[sendL] = (queueHead[sendL] + sendN) % queueMax
            queueLen[sendL] -= sendN
            linkSent[sendL] += sendN
            curP[ids] = G.nextP[pktL]
            curS[ids] = G.nextS[pktL]
            onLink[ids] = pktL
            slotOf = (t + G.linkDelay[pktL] + P.processingDelay) % numSlots
            for sl in np.unique(slotOf):
                arrivalSlot[sl].extend(ids[slotOf == sl].tolist())
            if nlog is not None:
                nlog.sent(sendL, sendN, pktL, ids)

        timeline[t - 1, :] = [numPackets, *statusCount]
        if nlog is not None:
            nlog.record(t, queueLen, queueBuf, queueHead, queueMax, genTime)
        if recordAnim and t <= animSteps:
            animQueue[:, t - 1] = queueLen
            animInFlight[:, t - 1] = np.bincount(onLink[onLink >= 0], minlength=numLinks)
        hist.record(t, queueLen)
        if stepHook is not None:
            stepHook(t, queueLen, status, curP, curS, onLink, numPackets)

        if t >= P.simTime and numPackets == statusCount.sum():   # 진행 중인 패킷 없음
            break

    if nlog is not None and t % nlog.interval:   # 마지막 기록 이후 남은 구간
        nlog.record(t, queueLen, queueBuf, queueHead, queueMax, genTime, force=True)

    R = SimpleNamespace()
    R.routeName = routeName
    R.genRate = genRate
    R.epsilon = epsilon
    R.numPackets = numPackets
    R.endStep = t
    R.genTime = genTime[:numPackets]
    R.endTime = endTime[:numPackets]
    R.hops = hops[:numPackets]
    R.status = status[:numPackets]
    R.decisionLog = decisionLog[:numDecisions, :]
    R.timeline = timeline[:t, :]
    R.grid = G
    R.linkSent = linkSent
    R.bg = bgStat
    R.bg['inFlight'] = bgPool - len(bgFree)
    R.nodeLog = nlog.table() if nlog is not None else None   # node_log.NODE_LOG_COLUMNS 순서
    if recordAnim:
        R.animQueue = animQueue[:, :min(animSteps, t)]
        R.animInFlight = animInFlight[:, :min(animSteps, t)]
    return R
