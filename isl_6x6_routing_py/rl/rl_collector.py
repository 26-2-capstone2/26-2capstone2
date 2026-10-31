# 경험 연결 장치 - 시뮬레이터가 돌아가는 동안 route_C의 결정을 (s, a, r, s', done) 경험으로 이어 붙여 버퍼에 넣고 학습
#
# 패킷 하나의 흐름
#   위성 A에서 결정 -> (결과를 아직 모름, 대기 pending에 보관)
#   위성 B에서 결정 -> A의 경험 완성: s = A 관측, s' = B 관측, done = 0, r = A 홉 보상
#   ... 패킷이 끝남 (도착 또는 손실) -> 손실이면 앞뒤 패킷 결과로 단발/연속 손실이 정해질 때까지 기다렸다가 마지막 경험 완성
#       연속 손실(패킷 번호 순서로 3개 이상)이면 처음 2개를 포함한 구간 전체가 연속 손실 보상을 받음
#   큐가 꽉 차서 바로 버려진 결정도 같은 종료 처리에 넣음
#
# 시뮬레이터(sim/run_isl_sim.py)가 부르는 곳
#   on_decision(): 5. 라우팅 결정 직후 (route_C일 때만)
#   on_end():      1~3. 도착, 기한 초과, TTL 만료 처리 직후
from dataclasses import dataclass

import numpy as np

from rl.rl_reward import LOSS_STATUS, burst_extra, hop_reward, terminal_reward


@dataclass(frozen=True)
class PendingHop:
    obs: np.ndarray
    action: int
    hopReward: float


class Collector:
    def __init__(self, agent, P, RL, learn=True):
        self.agent = agent
        self.P = P
        self.RL = RL
        self.learn = learn                 # False면 경험만 모으고 학습 안 함
        self.zeroObs = np.zeros(RL.obsDim, dtype=np.float32)
        self.zeroMask = np.zeros(RL.numActions, dtype=np.float32)
        self.reset_stats()

    def reset_stats(self):
        # packet_id는 시뮬레이션 에피소드마다 0부터 다시 시작한다
        self.pending = {}                  # packet_id -> 다음 위성 도착을 기다리는 홉
        self.outcomes = {}                 # packet_id -> 확정된 패킷 상태
        self.terminalPending = {}          # packet_id -> 단발/연속 손실 판정을 기다리는 마지막 홉
        self.numTransitions = 0
        self.numBurstPenalties = 0         # 연속 손실 보상을 받은 패킷 수
        self.rewardHopSum = 0.0
        self.rewardOutcomeSum = 0.0
        self.rewardBurstSum = 0.0
        self.losses = []

    def on_decision(self, packetId, last, queueLenAtLink, enqueued):
        # last: route_C가 남긴 (관측, 마스크, 행동), queueLenAtLink: 고른 링크의 큐 길이 (넣기 전)
        obs, mask, action = last
        r = hop_reward(action + 1, queueLenAtLink, self.P, self.RL)
        self.rewardHopSum += r

        prev = self.pending.pop(packetId, None)
        if prev is not None:   # 이 패킷의 직전 결정이 이번 관측으로 완성됨
            self._push(prev.obs, prev.action, prev.hopReward, obs, 0.0, mask)

        current = PendingHop(obs, action, r)
        if enqueued:
            self.pending[packetId] = current
        else:                  # 큐 오버플로: 이 결정에서 바로 끝
            self._record_terminal(packetId, current, 4)

        if self.learn and self.agent.ready():
            self.losses.append(self.agent.learn())

    def on_end(self, endedIds, status):
        # 이번 step에 끝난 패킷들 (도착, 목적지 기한 초과, 중간 기한 초과, TTL 만료)
        for packetId in endedIds:
            prev = self.pending.pop(int(packetId), None)
            st = int(status[packetId])
            self._record_terminal(int(packetId), prev, st)

    def finish(self):
        # 에피소드 끝: 뒤 패킷이 없어 기다리던 손실을 마저 판정한다 (없는 패킷은 손실이 아닌 것으로 봄)
        for packetId in sorted(self.terminalPending):
            self._flush_terminal(packetId, final=True)
        dropped = len(self.pending)        # 끝나지 않은 패킷의 홉 (경험으로 만들지 않음)
        self.pending.clear()
        self.terminalPending.clear()
        self.outcomes.clear()
        return dropped

    def _record_terminal(self, packetId, last, st):
        if packetId in self.outcomes:
            raise ValueError(f'패킷 {packetId}의 종료가 두 번 기록됐습니다')
        self.outcomes[packetId] = st
        if last is not None:
            self.terminalPending[packetId] = last
        # 방금 끝난 패킷 때문에 판정이 가능해진 패킷이 있을 수 있음 (앞뒤로 기다리던 손실)
        for candidate in sorted(self.terminalPending):
            self._flush_terminal(candidate)

    def _burst_position(self, packetId, final):
        # 손실 패킷이 연속 손실 구간의 몇 번째인지 (단발 손실이면 0, 아직 모르면 None)
        isLoss = lambda j: self.outcomes.get(j) in LOSS_STATUS
        k = 1
        j = packetId - 1
        while j >= 0:                      # 앞쪽으로 이어진 손실 세기
            if j not in self.outcomes:
                if not final:
                    return None
                break
            if not isLoss(j):
                break
            k += 1
            j -= 1
        if k >= self.P.burstMinLen:
            return k
        for j in range(packetId + 1, packetId + 1 + self.P.burstMinLen - k):   # 뒤쪽 손실로 3개가 채워지는지
            if j not in self.outcomes:
                if not final:
                    return None
                return 0
            if not isLoss(j):
                return 0
        return k

    def _flush_terminal(self, packetId, final=False):
        last = self.terminalPending.get(packetId)
        if last is None:
            return
        st = self.outcomes[packetId]
        k = 0
        if st in LOSS_STATUS and self.RL.burstEnabled:
            k = self._burst_position(packetId, final)
            if k is None:
                return
        outcomeR = terminal_reward(st, self.RL)
        burstR = burst_extra(k, self.P, self.RL) if k > 0 else 0.0
        self.rewardOutcomeSum += outcomeR
        self.rewardBurstSum += burstR
        self.numBurstPenalties += int(k > 0)
        self._push(last.obs, last.action, last.hopReward + outcomeR + burstR, self.zeroObs, 1.0, self.zeroMask)
        del self.terminalPending[packetId]

    def _push(self, obs, action, reward, nextObs, done, nextMask):
        self.agent.remember(obs, action, reward, nextObs, done, nextMask)
        self.numTransitions += 1
