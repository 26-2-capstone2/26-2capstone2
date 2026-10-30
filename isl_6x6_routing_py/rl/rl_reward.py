# 보상 함수 - 보상 계산을 여기 한 곳에 모아, 식을 바꿔도 다른 코드는 안 고치게 함
#
#   매 홉:   -(고른 링크 지연 + 그 큐 길이 ÷ 링크 용량) ÷ 70   (빠르고 덜 막힌 길일수록 벌점이 작음)
#   끝:      기한 내 도착 +1, 손실(목적지 기한 초과, 중간 기한 초과, 큐 오버플로, TTL 만료) -1
#   연속 손실 (2차): 손실인데 바로 앞 패킷도 손실이면 추가 -consecPenalty (지금은 0, 팀원 작업 후 켬)
#
# 패킷 상태 status (sim/run_isl_sim.py): 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

ON_TIME = 1
LOSS_STATUS = (2, 3, 4, 5)


def hop_reward(nextDir, queueLenAtLink, P, RL):
    # 방향 하나를 골랐을 때의 즉시 보상 (nextDir: 1 상, 2 하, 3 좌, 4 우, queueLenAtLink: 고른 링크의 큐 길이)
    delay = P.linkDelay[nextDir - 1]
    return -(delay + queueLenAtLink / P.linkCapacity) / RL.rewardHopScale


def terminal_reward(status, RL, prevLost=False):
    # 패킷이 끝났을 때의 보상 (마지막 결정에 더함)
    # prevLost: 바로 앞 패킷도 손실이었는지 (연속 손실 판단은 팀원의 패킷 번호 기준으로 바꿀 예정)
    if status == ON_TIME:
        return RL.rewardOnTime
    if status in LOSS_STATUS:
        r = RL.rewardLoss
        if prevLost:
            r -= RL.consecPenalty
        return r
    raise ValueError(f'끝나지 않은 패킷 상태: {status}')
