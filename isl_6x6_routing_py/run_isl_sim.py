# 시뮬레이션 1회 실행 - 매 step(1 ms) 도착→확인→생성→라우팅→전송을 반복하고 결정 기록을 남김
#
import math
import warnings
from types import SimpleNamespace

import numpy as np

from build_grid import build_grid
from route_A import route_A
from route_B import route_B
from bg_traffic import make_bg_schedule, xy_next_dir
from node_log import NodeLog

# 라우팅 알고리즘 (config_isl.py P.routeName으로 고름, 입력/출력이 같아서 바꿔 끼우기만 하면 됨)
ROUTES = {'routeA': route_A, 'routeB': route_B}
ROUTE_LABELS = {'routeA': 'A 최단 경로', 'routeB': 'B 부하 고려', 'routeC': 'C 강화학습'}


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
    route = ROUTES[P.routeName]
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
    linkSent = np.zeros(numLinks, dtype=np.int64)

    # 도착 예정 패킷 (도착 step별 칸, 원형)
    numSlots = int(max(P.linkDelay)) + P.processingDelay + 1
    arrivalSlot = [[] for _ in range(numSlots)]

    # 결정 기록 (라우팅 결정 1번 = 1줄)
    decisionLog = np.zeros((max(maxPackets, 1) * 12, 24))
    numDecisions = 0

    maxSteps = P.simTime + P.maxDrainTime
    nodeLog = NodeLog(P, G, maxPackets) if getattr(P, 'nodeLogEnable', False) else None   # 노드 기준 기록 (node_log.py)
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
        if nodeLog and overDeadline.any():
            ids = inTransit[overDeadline]
            nodeLog.add(2, nodeLog.node(curP[ids], curS[ids]))
        inTransit = inTransit[~overDeadline]
        ttlExpired = ttl[inTransit] <= 0
        status[inTransit[ttlExpired]] = 5
        endTime[inTransit[ttlExpired]] = t
        if nodeLog and arrived.size:
            if ttlExpired.any():
                ids = inTransit[ttlExpired]
                nodeLog.add(3, nodeLog.node(curP[ids], curS[ids]))
            nodeLog.count[nodeLog.dstNode, 4] += len(onTimeIds)
            nodeLog.count[nodeLog.dstNode, 5] += len(lateIds)
        inTransit = inTransit[~ttlExpired]
        statusCount += [len(onTimeIds), len(lateIds), int(overDeadline.sum()), 0, int(ttlExpired.sum())]

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
        bgNew = []
        if bgOn and t <= P.simTime:
            for f in np.flatnonzero(bgCount[:, t]):
                n = int(bgCount[f, t])
                k = min(n, len(bgFree))
                bgStat['generated'] += n
                bgStat['srcDrop'] += n - k
                if k > 0:
                    ids = np.array([bgFree.pop() for _ in range(k)], dtype=np.int64)
                    (sp, ss), (dp, ds) = P.bgFlows[f]
                    genTime[ids] = t
                    ttl[ids] = P.bgTtl
                    hops[ids] = 0
                    curP[ids] = sp
                    curS[ids] = ss
                    dstP[ids] = dp
                    dstS[ids] = ds
                    onLink[ids] = -1
                    bgNew.append(ids)

        # 4-C. 배경 패킷 큐 진입 (XY 고정 경로)
        bgIds = np.concatenate([bgRoute] + bgNew)
        if len(bgIds):
            bp = curP[bgIds]
            bs = curS[bgIds]
            bd = xy_next_dir(bp, bs, dstP[bgIds], dstS[bgIds])
            bl = G.linkId[bp, bs, bd - 1]
            order = np.argsort(bl, kind='stable')
            bgIds = bgIds[order]
            bl = bl[order]
            for link in np.unique(bl):
                ids = bgIds[bl == link]
                k = int(min(len(ids), queueMax - queueLen[link]))
                if k > 0:
                    pos = (queueHead[link] + queueLen[link] + np.arange(k)) % queueMax
                    queueBuf[link, pos] = ids[:k]
                    queueLen[link] += k
                if k < len(ids):
                    lost = ids[k:]
                    bgStat['overflow'] += len(lost)
                    bgFree.extend(lost.tolist())
                    if nodeLog:
                        nodeLog.count[nodeLog.linkNode[link], 1] += len(lost)

        # 5. 라우팅 결정 (도착 패킷 -> 생성 패킷 순)
        toRoute = np.concatenate([inTransit, newIds])
        for packet_id in toRoute:
            p = int(curP[packet_id])
            s = int(curS[packet_id])
            nextDir, choiceType, L, N = route(p, s, queueLen, G, P)
            if epsilon > 0 and rng.random_sample() < epsilon:
                dirs = G.validDirs[p][s]
                nextDir = dirs[math.ceil(rng.random_sample() * len(dirs)) - 1]
                choiceType = 4   # 무작위

            link = G.linkId[p, s, nextDir - 1]
            enqueued = queueLen[link] < queueMax

            qNow = [-1] * 4
            for d, l in zip(G.validDirs[p][s], G.outLinks[p][s]):
                qNow[d - 1] = queueLen[l]

            if numDecisions >= decisionLog.shape[0]:
                decisionLog = np.vstack([decisionLog, np.zeros_like(decisionLog)])
            decisionLog[numDecisions, :] = [t, packet_id, hops[packet_id], p, s, *qNow, *L, *N,
                                            G.dstSat[0] - p, G.dstSat[1] - s,
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
                if nodeLog:
                    nodeLog.count[nodeLog.node(p, s), 0] += 1

        # 6. 전송: 링크마다 큐 앞쪽 최대 linkCapacity개
        if nodeLog:
            nodeLog.peak(queueLen)
        for link in np.flatnonzero(queueLen > 0):
            n = min(queueLen[link], P.linkCapacity)
            pos = (queueHead[link] + np.arange(n)) % queueMax
            ids = queueBuf[link, pos]
            queueHead[link] = (queueHead[link] + n) % queueMax
            queueLen[link] -= n
            linkSent[link] += n
            curP[ids] = G.nextP[link]
            curS[ids] = G.nextS[link]
            arriveSlot = (t + G.linkDelay[link] + P.processingDelay) % numSlots
            arrivalSlot[arriveSlot].extend(ids.tolist())
            onLink[ids] = link
            if nodeLog:
                nodeLog.sent(link, n, np.full(n, link), ids)

        timeline[t - 1, :] = [numPackets, *statusCount]
        if nodeLog:
            nodeLog.record(t, queueLen, queueBuf, queueHead, queueMax, genTime)
        if recordAnim and t <= animSteps:
            animQueue[:, t - 1] = queueLen
            animInFlight[:, t - 1] = np.bincount(onLink[onLink >= 0], minlength=numLinks)

        if t >= P.simTime and numPackets == statusCount.sum():   # 진행 중인 패킷 없음
            break

    if nodeLog and t % nodeLog.interval:
        nodeLog.record(t, queueLen, queueBuf, queueHead, queueMax, genTime, force=True)   # 마지막 남은 구간

    R = SimpleNamespace()
    R.genRate = genRate
    R.epsilon = epsilon
    R.routeName = P.routeName
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
    R.nodeLog = nodeLog.table() if nodeLog else None   # 노드 기록 (열: node_log.NODE_LOG_COLUMNS)
    if recordAnim:
        R.animQueue = animQueue[:, :min(animSteps, t)]
        R.animInFlight = animInFlight[:, :min(animSteps, t)]
    return R
