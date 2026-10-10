# 성능 평가 지표 계산 - 시뮬레이션 결과로 지표 7개와 손실 원인별 개수를 계산
#
from types import SimpleNamespace

import numpy as np


def compute_metrics(R, P):
    # 성능 평가 지표 7개 + 손실 원인별 개수
    status = R.status
    onTime = status == 1                          # 기한 내 도착
    reachedDst = (status == 1) | (status == 2)    # 목적지에 도착한 패킷 (기한 초과 포함)

    M = SimpleNamespace()
    M.routeName = R.routeName
    M.genRate = R.genRate
    M.epsilon = R.epsilon
    M.generated = R.numPackets
    M.onTime = int(onTime.sum())
    M.lateAtDst = int((status == 2).sum())
    M.lateMid = int((status == 3).sum())
    M.overflow = int((status == 4).sum())
    M.ttlExpired = int((status == 5).sum())

    # Average Latency: 도착 패킷의 (종료 - 생성) 평균 [논문 식 13]
    M.avgLatency_ms = float(np.mean(R.endTime[reachedDst] - R.genTime[reachedDst])) * P.stepTime * 1e3

    # Packet Loss Rate: 손실 수 / 생성 수 [논문 식 14]
    M.lossRate = float((R.numPackets - onTime.sum()) / R.numPackets)

    # Throughput: 성공 수 x 패킷 크기 / 시뮬레이션 시간 [논문 식 15], 시간 = 생성 기간
    M.throughput_Mbps = float(onTime.sum() * P.packetSize * 8 / (P.simTime * P.stepTime) / 1e6)

    # On-time Delivery Rate
    M.onTimeRate = float(onTime.sum() / R.numPackets)

    # Consecutive Packet Loss Length: 패킷 id 순서로 연속 손실 최대 길이
    lossFlag = ~onTime
    if hasattr(R, 'packetEpisode'):   # 에피소드 경계에서는 연속 손실이 이어지지 않게 끊음
        cut = np.flatnonzero(np.diff(R.packetEpisode)) + 1
        lossFlag = np.insert(lossFlag, cut, False)
    edge = np.diff(np.concatenate([[0], lossFlag.astype(int), [0]]))
    runLengths = np.flatnonzero(edge == -1) - np.flatnonzero(edge == 1)
    M.maxConsecLoss = int(runLengths.max()) if runLengths.size else 0

    # Route Change Count: 도착 패킷끼리 id 순서로 직전 패킷과 경로가 다른 횟수
    D = R.decisionLog[R.decisionLog[:, 23] == 1, :]
    D = D[np.lexsort((D[:, 2], D[:, 1]))]
    pktIdx = D[:, 1].astype(int)
    satNode = (D[:, 3] * P.satsPerPlane + D[:, 4]).astype(int)
    paths = [None] * R.numPackets
    first = np.concatenate([[0], np.flatnonzero(np.diff(pktIdx)) + 1])
    last = np.concatenate([first[1:], [len(pktIdx)]])
    for f, l in zip(first, last):
        paths[pktIdx[f]] = tuple(satNode[f:l])
    reachedIds = np.flatnonzero(reachedDst)
    numChanges = 0
    for j in range(1, len(reachedIds)):
        sameEp = (not hasattr(R, 'packetEpisode')) or R.packetEpisode[reachedIds[j]] == R.packetEpisode[reachedIds[j - 1]]
        if sameEp and paths[reachedIds[j]] != paths[reachedIds[j - 1]]:   # 에피소드가 바뀌는 곳은 세지 않음
            numChanges += 1
    M.routeChanges = numChanges

    # Average Hop Count: 도착 패킷의 홉 수 평균
    M.avgHops = float(np.mean(R.hops[reachedDst]))

    # 배경 트래픽 개수 (위 지표는 모두 주 흐름만으로 계산)
    M.bgGenerated = int(R.bg['generated'])
    M.bgDelivered = int(R.bg['delivered'])
    M.bgOverflow = int(R.bg['overflow'])
    M.bgTtlExpired = int(R.bg['ttlExpired'])
    M.bgSrcDrop = int(R.bg['srcDrop'])   # 배경 패킷 자리가 모자라 못 만든 수 (0이어야 정상)
    return M
