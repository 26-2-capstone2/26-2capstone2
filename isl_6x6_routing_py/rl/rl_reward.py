# 보상 함수 - 보상 계산을 여기 한 곳에 모아, 식을 바꿔도 다른 코드는 안 고치게 함
#
#   매 홉:     -(고른 링크 지연 + 그 큐 길이 ÷ 링크 용량) ÷ 70   (빠르고 덜 막힌 길일수록 벌점이 작음)
#   끝:        기한 내 도착 +1
#              단발 손실 (패킷 번호 순서로 1~2개만 이어진 손실) -0.5
#              연속 손실 (3개 이상 이어진 손실) k번째 패킷 -min(2.0, 1.0 + 0.1 x max(0, k - 3))
#                -> 구간 전체(처음 2개 포함)에 단발 손실 대신 적용, 길이에 따라 -1.0 ~ -2.0
#   손실 = 목적지 기한 초과, 중간 기한 초과, 큐 오버플로, TTL 만료
#
# 패킷 상태 status (sim/run_isl_sim.py): 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

ON_TIME = 1
LOSS_STATUS = (2, 3, 4, 5)


def hop_reward(nextDir, queueLenAtLink, P, RL):
    # 방향 하나를 골랐을 때의 즉시 보상 (nextDir: 1 상, 2 하, 3 좌, 4 우, queueLenAtLink: 고른 링크의 큐 길이)
    delay = P.linkDelay[nextDir - 1]
    return -(delay + queueLenAtLink / P.linkCapacity) / RL.rewardHopScale


def terminal_reward(status, RL):
    # 패킷 자체의 도착/단발 손실 보상. 연속 손실은 burst_extra로 더한다.
    if status == ON_TIME:
        return RL.rewardOnTime
    if status in LOSS_STATUS:
        return RL.rewardSingleLoss
    raise ValueError(f'끝나지 않은 패킷 상태: {status}')


def burst_reward(k, P, RL):
    # 연속 손실 구간에서 k번째(1부터) 패킷의 끝 보상
    return -min(RL.burstMax, RL.burstBase + RL.burstStep * max(0, k - P.burstMinLen))


def burst_extra(k, P, RL):
    # 연속 손실 패킷이 단발 손실 대신 받는 보상과의 차이 (기록을 도착/단발 보상과 연속 손실 몫으로 나누기 위함)
    return burst_reward(k, P, RL) - RL.rewardSingleLoss
