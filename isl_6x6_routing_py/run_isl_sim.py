# 시뮬레이션 1회 실행 - 매 step(1 ms) 도착→확인→생성→라우팅→전송을 반복하고 결정 기록을 남김
#
import math
import warnings
from types import SimpleNamespace

import numpy as np

from build_grid import build_grid
from route_B import route_B


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
    genTime = np.zeros(maxPackets, dtype=np.int64)   # 생성 시각
    ttl = np.zeros(maxPackets, dtype=np.int64)       # 남은 TTL
    hops = np.zeros(maxPackets, dtype=np.int64)      # 지금까지 홉 수
    curP = np.zeros(maxPackets, dtype=np.int64)      # 현재 위성 p (전송 중이면 다음 위성)
    curS = np.zeros(maxPackets, dtype=np.int64)      # 현재 위성 s
    status = np.zeros(maxPackets, dtype=np.int64)    # 패킷 상태 (위 설명)
    endTime = np.zeros(maxPackets, dtype=np.int64)   # 종료 step
    onLink = np.full(maxPackets, -1, dtype=np.int64) # 타고 있는 링크 번호 (애니메이션용, -1: 링크 위 아님)
    statusCount = np.zeros(5, dtype=np.int64)        # 상태별 누적 개수 (status = 1~5)

    # 도착 예정 패킷 (도착 step별 칸, 원형)
    numSlots = int(max(P.linkDelay)) + P.processingDelay + 1
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
        inTransit = inTransit[~overDeadline]
        ttlExpired = ttl[inTransit] <= 0
        status[inTransit[ttlExpired]] = 5
        endTime[inTransit[ttlExpired]] = t
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

        # 5. 라우팅 결정 (도착 패킷 -> 생성 패킷 순)
        toRoute = np.concatenate([inTransit, newIds])
        for packet_id in toRoute:
            p = int(curP[packet_id])
            s = int(curS[packet_id])
            nextDir, choiceType, L, N = route_B(p, s, queueLen, G, P)
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

        # 6. 전송: 링크마다 큐 앞쪽 최대 linkCapacity개
        for link in np.flatnonzero(queueLen > 0):
            n = min(queueLen[link], P.linkCapacity)
            pos = (queueHead[link] + np.arange(n)) % queueMax
            ids = queueBuf[link, pos]
            queueHead[link] = (queueHead[link] + n) % queueMax
            queueLen[link] -= n
            curP[ids] = G.nextP[link]
            curS[ids] = G.nextS[link]
            arriveSlot = (t + G.linkDelay[link] + P.processingDelay) % numSlots
            arrivalSlot[arriveSlot].extend(ids.tolist())
            onLink[ids] = link

        timeline[t - 1, :] = [numPackets, *statusCount]
        if recordAnim and t <= animSteps:
            animQueue[:, t - 1] = queueLen
            animInFlight[:, t - 1] = np.bincount(onLink[onLink >= 0], minlength=numLinks)

        if t >= P.simTime and numPackets == statusCount.sum():   # 진행 중인 패킷 없음
            break

    R = SimpleNamespace()
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
    if recordAnim:
        R.animQueue = animQueue[:, :min(animSteps, t)]
        R.animInFlight = animInFlight[:, :min(animSteps, t)]
    return R
