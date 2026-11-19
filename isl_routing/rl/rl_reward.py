# 보상 함수 : 보상 계산을 여기 한 곳에 모아, 식을 바꿔도 다른 코드는 안 고치게 함
#
#   매 홉:     -고른 링크 지연 ÷ 기한 상한 (RL.rewardHopQueue = True면 큐 길이 ÷ 링크 용량도 더함)
#   끝:        기한 내 도착 +0.5
#              단발 손실 (같은 흐름에서 패킷 번호 순서로 1~2개만 이어진 손실) -0.1
#              연속 손실 (3개 이상 이어진 손실) k번째 패킷 -min(1.0, 0.2 + 0.1 x max(0, k - 3))
#                -> 구간 전체(처음 2개 포함)에 단발 손실 대신 적용, 길이에 따라 -0.2 ~ -1.0
#              + 시작 벌점: 3번째 패킷(연속 손실이 되는 순간)에 -0.5 한 번 (RL.burstStartPenalty)
#                -> 같은 개수를 잃어도 쪼갤수록 벌점이 작던 문제 보완 (연속 손실 횟수를 줄이게)
#   손실 = 목적지 기한 초과, 중간 기한 초과, 큐 오버플로, TTL 만료
#
# 패킷 상태 status (sim/run_isl_sim.py): 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

ON_TIME = 1
LOSS_STATUS = (2, 3, 4, 5)


def hop_reward(delay, queueLenAtLink, P, RL):
    # 방향 하나를 골랐을 때의 즉시 보상 (delay: 고른 링크의 지연 step, queueLenAtLink: 고른 링크의 큐 길이)
    if not getattr(RL, 'rewardHopQueue', True):   # 큐 힌트 없는 홉 보상
        return -delay / RL.rewardHopScale
    return -(delay + queueLenAtLink / P.linkCapacity) / RL.rewardHopScale


def terminal_reward(status, RL):
    # 패킷 자체의 도착/단발 손실 보상. 연속 손실은 burst_extra로 더한다.
    if status == ON_TIME:
        return RL.rewardOnTime
    if status in LOSS_STATUS:
        return RL.rewardSingleLoss
    raise ValueError(f'끝나지 않은 패킷 상태: {status}')


def burst_reward(k, P, RL):
    # 연속 손실 구간에서 k번째(1부터) 패킷의 끝 보상. 구간이 시작되는 패킷(k = 3)은 시작 벌점을 한 번 더 받음
    start = getattr(RL, 'burstStartPenalty', 0.0) if k == P.burstMinLen else 0.0
    return -min(RL.burstMax, RL.burstBase + RL.burstStep * max(0, k - P.burstMinLen)) - start


def burst_extra(k, P, RL):
    # 연속 손실 패킷이 단발 손실 대신 받는 보상과의 차이
    return burst_reward(k, P, RL) - RL.rewardSingleLoss
