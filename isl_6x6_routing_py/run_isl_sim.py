# 시뮬레이션 1회 실행 - 매 step(1 ms) 도착→확인→생성→라우팅→전송을 반복하고 결정 기록을 남김
#
import math
import warnings
from types import SimpleNamespace

import numpy as np

from build_grid import build_grid
from node_log import NodeLog
from route_A import route_A
from route_B import route_B

# 라우팅 알고리즘 (config_isl.py P.routeName으로 고름, 입력/출력이 같아서 바꿔 끼우기만 하면 됨)
ROUTES = {'routeA': route_A, 'routeB': route_B}
ROUTE_LABELS = {'routeA': 'A 최단 경로', 'routeB': 'B 부하 고려', 'routeC': 'C 강화학습'}

# CSV 열 이름 (main_isl, run_experiments에서 사용)
DECISION_LOG_COLUMNS = ['step', 'packet_id', 'hop', 'cur_p', 'cur_s',
                        'q_up', 'q_down', 'q_left', 'q_right',
                        'L_up', 'L_down', 'L_left', 'L_right',
                        'N_up', 'N_down', 'N_left', 'N_right',
                        'rem_dp', 'rem_ds', 'rem_deadline', 'ttl',
                        'action', 'choice_type', 'enqueued']
# action: 1 상, 2 하, 3 좌, 4 우 / choice_type: 1 주, 2 대체, 3 우회, 4 무작위
PACKET_LOG_COLUMNS = ['packet_id', 'gen_step', 'end_step', 'result', 'hops']
# result: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료


def packet_log_table(R):
    # packet_log CSV용 표 (패킷 1개 = 1줄)
    return np.column_stack([np.arange(R.numPackets), R.genTime, R.endTime, R.status, R.hops])


def writetable(rows, columns, path, fmt):
    np.savetxt(path, rows, delimiter=',', header=','.join(columns), comments='', fmt=fmt)


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

    # 배경 패킷은 주 흐름 뒤 번호를 씀: id = maxPackets + 풀 칸 번호 (끝난 칸은 다시 사용)
    bgEnable = getattr(P, 'bgEnable', False)
    bgPool = P.bgPoolSize if bgEnable else 0
    numIds = maxPackets + bgPool

    genTime = np.zeros(maxPackets, dtype=np.int64)   # 생성 시각
    ttl = np.zeros(numIds, dtype=np.int64)           # 남은 TTL
    hops = np.zeros(numIds, dtype=np.int64)          # 지금까지 홉 수
    curP = np.zeros(numIds, dtype=np.int64)          # 현재 위성 p (전송 중이면 다음 위성)
    curS = np.zeros(numIds, dtype=np.int64)          # 현재 위성 s
    status = np.zeros(maxPackets, dtype=np.int64)    # 패킷 상태 (위 설명)
    endTime = np.zeros(maxPackets, dtype=np.int64)   # 종료 step
    onLink = np.full(numIds, -1, dtype=np.int64)     # 타고 있는 링크 번호 (애니메이션용, -1: 링크 위 아님)
    statusCount = np.zeros(5, dtype=np.int64)        # 상태별 누적 개수 (status = 1~5)

    # 배경 트래픽: 흐름마다 ON/OFF 반복 (길이는 지수분포), ON이면 bgOnRate개/step 생성
    bgCount = np.zeros(5, dtype=np.int64)   # 누적: 생성, 목적지 도착, 큐 오버플로, TTL 만료, 풀 부족으로 생성 못 함
    if bgEnable:
        bgRng = np.random.RandomState(P.bgSeed)   # 주 흐름 난수(ε)와 분리 -> 실행마다 같은 배경 패턴
        bgDstP = np.zeros(numIds, dtype=np.int64)   # 배경 패킷 도착 위성 p
        bgDstS = np.zeros(numIds, dtype=np.int64)   # 배경 패킷 도착 위성 s
        bgFree = list(range(numIds - 1, maxPackets - 1, -1))   # 비어 있는 배경 id (스택)
        numFlows = len(P.bgFlows)
        bgRate = np.asarray(P.bgOnRate, dtype=float)
        bgOn = bgRng.random_sample(numFlows) < P.bgOnMean / (P.bgOnMean + P.bgOffMean)   # 시작 상태
        bgLeft = [bg_duration(bgRng, P.bgOnMean if on else P.bgOffMean) for on in bgOn]  # 남은 ON/OFF 길이
        bgCredit = np.zeros(numFlows)   # 소수 생성률 누적 (5.5면 5, 6, 5, 6 ...개)

    # 도착 예정 패킷 (도착 step별 칸, 원형)
    numSlots = int(max(P.linkDelay)) + P.processingDelay + 1
    arrivalSlot = [[] for _ in range(numSlots)]

    # 결정 기록 (라우팅 결정 1번 = 1줄)
    decisionLog = np.zeros((max(maxPackets, 1) * 12, 24))
    numDecisions = 0

    maxSteps = P.simTime + P.maxDrainTime
    nodeLog = NodeLog(P, G, maxPackets) if getattr(P, 'nodeLogEnable', False) else None   # 노드 기준 기록
    timeline = np.zeros((maxSteps, 6), dtype=np.int64)   # 누적: 생성, 기한 내 도착, 목적지 기한 초과, 중간 기한 초과, 오버플로, TTL 만료
    if recordAnim:
        animSteps = min(P.animDuration, maxSteps)
        animQueue = np.zeros((numLinks, animSteps), dtype=np.uint16)     # step별 링크 큐 길이
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
        arrivedAll = np.array(sorted(arrivalSlot[slot]), dtype=np.int64)
        arrivalSlot[slot] = []
        onLink[arrivedAll] = -1
        hops[arrivedAll] += 1
        ttl[arrivedAll] -= 1
        arrived = arrivedAll[arrivedAll < maxPackets]   # 주 흐름 패킷

        # 배경 패킷: 목적지 도착 -> TTL 만료 확인 (기한 없음), 끝난 id는 반납
        bgInTransit = arrivedAll[arrivedAll >= maxPackets]
        if bgInTransit.size:
            bgAtDst = (curP[bgInTransit] == bgDstP[bgInTransit]) & (curS[bgInTransit] == bgDstS[bgInTransit])
            bgDead = ~bgAtDst & (ttl[bgInTransit] <= 0)
            bgCount[1] += int(bgAtDst.sum())
            bgCount[3] += int(bgDead.sum())
            bgFree.extend(bgInTransit[bgAtDst | bgDead].tolist())
            bgInTransit = bgInTransit[~(bgAtDst | bgDead)]

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

        # 4-1. 배경 패킷 생성 + 고정 경로로 큐에 넣기 (주 흐름 라우팅 전에 넣어서 주 흐름이 이번 부하를 봄)
        if bgEnable:
            bgNew = []
            for f in range(numFlows):
                if bgOn[f] and t <= P.simTime:
                    bgCredit[f] += bgRate[f]
                    n = int(bgCredit[f])
                    bgCredit[f] -= n
                    k = min(n, len(bgFree))
                    bgCount[4] += n - k
                    if k > 0:
                        ids = np.array(bgFree[-k:], dtype=np.int64)
                        del bgFree[-k:]
                        (sp, ss), (dp, ds) = P.bgFlows[f]
                        ttl[ids] = P.bgTtl
                        hops[ids] = 0
                        curP[ids], curS[ids] = sp, ss
                        bgDstP[ids], bgDstS[ids] = dp, ds
                        bgNew.append(ids)
                        bgCount[0] += k
                bgLeft[f] -= 1
                if bgLeft[f] <= 0:   # ON <-> OFF 전환
                    bgOn[f] = not bgOn[f]
                    bgLeft[f] = bg_duration(bgRng, P.bgOnMean if bgOn[f] else P.bgOffMean)
                    bgCredit[f] = 0.0
            bgIds = np.concatenate([bgInTransit] + bgNew)
            if bgIds.size:
                dropLinks = bg_enqueue(bgIds, curP, curS, bgDstP, bgDstS, G,
                                       queueBuf, queueHead, queueLen, queueMax, bgFree)
                bgCount[2] += len(dropLinks)
                if nodeLog:
                    nodeLog.add(1, nodeLog.linkNode[dropLinks])

        # 5. 라우팅 결정 (도착 패킷 -> 생성 패킷 순)
        toRoute = np.concatenate([inTransit, newIds])
        for packet_id in toRoute:
            p = int(curP[packet_id])
            s = int(curS[packet_id])
            nextDir, choiceType, L, N = route(p, s, queueLen, G, P)
            if epsilon > 0 and rng.random_sample() < epsilon:
                # 무작위: 라우팅이 고른 방향은 빼고 나머지 갈 수 있는 방향 중 하나 (탐험이 실제로 ε만큼 되게)
                dirs = [d for d in G.validDirs[p][s] if d != nextDir]   # Grid 모서리도 방향이 2개라 항상 1개 이상
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
        active = np.flatnonzero(queueLen > 0)
        if active.size:
            n = np.minimum(queueLen[active], P.linkCapacity)
            links = np.repeat(active, n)                               # 보내는 패킷마다 링크 번호
            offset = np.arange(len(links)) - np.repeat(np.cumsum(n) - n, n)   # 링크 안 순번 0, 1, ...
            ids = queueBuf[links, (queueHead[links] + offset) % queueMax]
            queueHead[active] = (queueHead[active] + n) % queueMax
            queueLen[active] -= n
            curP[ids] = G.nextP[links]
            curS[ids] = G.nextS[links]
            onLink[ids] = links
            arriveSlot = (t + G.linkDelay[links] + P.processingDelay) % numSlots
            for a in np.unique(arriveSlot):   # 링크 지연 종류(7, 2 step)별로 도착 칸에 넣기
                arrivalSlot[a].extend(ids[arriveSlot == a].tolist())
            if nodeLog:
                nodeLog.sent(active, n, links, ids)

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
    R.bgCount = bgCount   # 배경: 생성, 목적지 도착, 큐 오버플로, TTL 만료, 풀 부족
    R.nodeLog = nodeLog.table() if nodeLog else None   # 노드 기록 (열: node_log.NODE_LOG_COLUMNS)
    if recordAnim:
        R.animQueue = animQueue[:, :min(animSteps, t)]
        R.animInFlight = animInFlight[:, :min(animSteps, t)]
    return R


def bg_duration(rng, mean):
    # ON/OFF 길이 (step): 평균 mean인 지수분포, 최소 1 step
    return max(1, int(round(rng.exponential(mean))))


def bg_enqueue(ids, curP, curS, bgDstP, bgDstS, G, queueBuf, queueHead, queueLen, queueMax, bgFree):
    # 배경 패킷 고정 경로: 목적지 쪽 좌/우 먼저, 같은 열이면 상/하 (부하를 보지 않음)
    # 같은 링크에 여러 개면 ids 순서대로 넣고, 큐가 꽉 차면 버림 -> 버린 패킷의 링크 번호 반환
    p = curP[ids]
    s = curS[ids]
    dp = bgDstP[ids] - p
    ds = bgDstS[ids] - s
    d = np.where(dp != 0, np.where(dp > 0, 4, 3), np.where(ds > 0, 2, 1))
    links = G.linkId[p, s, d - 1]

    order = np.argsort(links, kind='stable')
    links = links[order]
    ids = ids[order]
    starts = np.flatnonzero(np.concatenate([[True], links[1:] != links[:-1]]))
    rank = np.arange(len(links)) - np.repeat(starts, np.diff(np.append(starts, len(links))))   # 링크 안 순번
    ok = rank < queueMax - queueLen[links]
    pos = (queueHead[links] + queueLen[links] + rank) % queueMax
    queueBuf[links[ok], pos[ok]] = ids[ok]
    np.add.at(queueLen, links[ok], 1)
    bgFree.extend(ids[~ok].tolist())
    return links[~ok]
