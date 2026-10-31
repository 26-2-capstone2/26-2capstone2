# 보상 함수 - 보상 계산을 여기 한 곳에 모아, 식을 바꿔도 다른 코드는 안 고치게 함
#
#   매 홉:   -(고른 링크 지연 + 그 큐 길이 ÷ 링크 용량) ÷ 70   (빠르고 덜 막힌 길일수록 벌점이 작음)
#   끝:      기한 내 도착 +1, 손실(목적지 기한 초과, 중간 기한 초과, 큐 오버플로, TTL 만료) -1
#   연속 손실: 현재 패킷과 생성 순서상 앞의 2개가 모두 손실이면 추가 -consecPenalty
#               길이 3 구간은 1회, 길이 4 구간은 2회 벌점을 받음
#
# 패킷 상태 status (sim/run_isl_sim.py): 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

ON_TIME = 1
LOSS_STATUS = (2, 3, 4, 5)


def hop_reward(nextDir, queueLenAtLink, P, RL):
    # 방향 하나를 골랐을 때의 즉시 보상 (nextDir: 1 상, 2 하, 3 좌, 4 우, queueLenAtLink: 고른 링크의 큐 길이)
    delay = P.linkDelay[nextDir - 1]
    return -(delay + queueLenAtLink / P.linkCapacity) / RL.rewardHopScale


def terminal_reward(status, RL):
    # 패킷 자체의 도착/손실 보상. 연속 손실 벌점과 분리해 기록한다.
    if status == ON_TIME:
        return RL.rewardOnTime
    if status in LOSS_STATUS:
        return RL.rewardLoss
    raise ValueError(f'끝나지 않은 패킷 상태: {status}')


def burst_reward(inBurst, RL):
    # 생성 순서상 burstMinLen번째 이후로 이어지는 실패에 대한 추가 벌점
    return -RL.consecPenalty if inBurst else 0.0
