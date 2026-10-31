# 성능 평가 지표 계산 - 시뮬레이션 결과로 지표 7개와 손실 원인별 개수를 계산
#
from types import SimpleNamespace

import numpy as np


def loss_run_lengths(status, packet_episode=None):
    """생성 순서의 실패 구간 길이. 시뮬레이션 에피소드 경계에서 구간을 끊는다."""
    status = np.asarray(status)
    if np.any(status == 0):
        raise ValueError(f'종료되지 않은 주 흐름 패킷 {int(np.sum(status == 0))}개: 지표 계산을 중단합니다')
    if np.any((status < 1) | (status > 5)):
        raise ValueError('알 수 없는 패킷 상태가 있습니다')
    loss_flag = status != 1
    if packet_episode is not None:
        packet_episode = np.asarray(packet_episode)
        if len(packet_episode) != len(status):
            raise ValueError('packet_episode 길이가 status와 다릅니다')
        cuts = np.flatnonzero(np.diff(packet_episode)) + 1
        loss_flag = np.insert(loss_flag, cuts, False)
    edge = np.diff(np.concatenate([[0], loss_flag.astype(int), [0]]))
    return np.flatnonzero(edge == -1) - np.flatnonzero(edge == 1)


def burst_summary(status, min_len, packet_episode=None):
    """길이 min_len 이상인 연속 실패 구간과 그 안의 패킷 비율."""
    if min_len < 2:
        raise ValueError('burstMinLen은 2 이상이어야 합니다')
    runs = loss_run_lengths(status, packet_episode)
    bursts = runs[runs >= min_len]
    return SimpleNamespace(
        burstCount=int(len(bursts)),
        burstPackets=int(bursts.sum()),
        burstPacketRate=float(bursts.sum() / len(status)) if len(status) else 0.0,
        maxConsecLoss=int(runs.max()) if len(runs) else 0,
        lossRuns=runs,
    )


def compute_metrics(R, P):
    # 성능 평가 지표 7개 + 손실 원인별 개수
    status = R.status
    burst = burst_summary(status, P.burstMinLen, getattr(R, 'packetEpisode', None))
    onTime = status == 1                          # 기한 내 도착
    reachedDst = (status == 1) | (status == 2)    # 목적지에 도착한 패킷 (기한 초과 포함)

    M = SimpleNamespace()
    M.routeName = R.routeName
    M.genRate = R.genRate
    M.epsilon = R.epsilon
    M.generated = R.numPackets
    M.unfinished = int((status == 0).sum())
    M.onTime = int(onTime.sum())
    M.lateAtDst = int((status == 2).sum())
    M.lateMid = int((status == 3).sum())
    M.overflow = int((status == 4).sum())
    M.ttlExpired = int((status == 5).sum())

    # Average Latency: 도착 패킷의 (종료 - 생성) 평균 [논문 식 13]
    M.avgLatency_ms = (float(np.mean(R.endTime[reachedDst] - R.genTime[reachedDst])) * P.stepTime * 1e3
                       if reachedDst.any() else float('nan'))

    # Packet Loss Rate: 손실 수 / 생성 수 [논문 식 14]
    M.lossRate = float((R.numPackets - onTime.sum()) / R.numPackets)

    # Throughput: 성공 수 x 패킷 크기 / 시뮬레이션 시간 [논문 식 15], 시간 = 생성 기간
    M.throughput_Mbps = float(onTime.sum() * P.packetSize * 8 / (P.simTime * P.stepTime) / 1e6)

    # On-time Delivery Rate
    M.onTimeRate = float(onTime.sum() / R.numPackets)

    # 연속 손실: 같은 흐름에서 생성 순서상 실패가 burstMinLen개 이상 이어진 구간
    M.burstMinLen = P.burstMinLen
    M.burstCount = burst.burstCount
    M.burstPackets = burst.burstPackets
    M.burstPacketRate = burst.burstPacketRate
    M.maxConsecLoss = burst.maxConsecLoss

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
