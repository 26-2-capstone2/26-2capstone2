# 경험 연결 장치 - 시뮬레이터가 돌아가는 동안 C_RL의 결정을 (s, a, r, s', done) 경험으로 이어 붙여 버퍼에 넣고 학습
#
# 패킷 하나의 흐름
#   위성 A에서 결정 -> (결과를 아직 모름, 대기 pending에 보관)
#   위성 B에서 결정 -> A의 경험 완성: s = A 관측, s' = B 관측, done = 0, r = A 홉 보상
#   ... 패킷이 끝남 (도착 또는 손실) -> 마지막 경험 완성: done = 1, r = 마지막 홉 보상 + 끝 보상
#   큐가 꽉 차서 바로 버려진 결정은 그 자리에서 끝 (done = 1, 손실 -1)
#
# 시뮬레이터(sim/run_isl_sim.py)가 부르는 곳
#   on_decision(): 5. 라우팅 결정 직후 (C_RL일 때만)
#   on_end():      1~3. 도착, 기한 초과, TTL 만료 처리 직후
import numpy as np

from rl.rl_reward import LOSS_STATUS, hop_reward, terminal_reward


class Collector:
    def __init__(self, agent, P, RL, learn=True):
        self.agent = agent
        self.P = P
        self.RL = RL
        self.learn = learn                 # False면 경험만 모으고 학습 안 함
        self.pending = {}                  # packet_id -> (관측, 마스크, 행동, 홉 보상): 다음 결정이나 끝을 기다리는 중
        self.zeroObs = np.zeros(RL.obsDim, dtype=np.float32)
        self.zeroMask = np.zeros(RL.numActions, dtype=np.float32)
        self.reset_stats()

    def reset_stats(self):
        # 에피소드마다 새로 셈
        self.numTransitions = 0
        self.numEnded = 0
        self.losses = []

    def on_decision(self, packetId, last, queueLenAtLink, enqueued, status):
        # last: C_RL이 남긴 (관측, 마스크, 행동), queueLenAtLink: 고른 링크의 큐 길이 (넣기 전)
        obs, mask, action = last
        r = hop_reward(action + 1, queueLenAtLink, self.P, self.RL)

        prev = self.pending.pop(packetId, None)
        if prev is not None:   # 이 패킷의 직전 결정이 이번 관측으로 완성됨
            pObs, pMask, pAction, pR = prev
            self._push(pObs, pAction, pR, obs, 0.0, mask)

        if enqueued:
            self.pending[packetId] = (obs, mask, action, r)
        else:                  # 큐 오버플로: 이 결정에서 바로 끝
            self._push(obs, action, r + self._terminal(packetId, 4, status), self.zeroObs, 1.0, self.zeroMask)
            self.numEnded += 1

        if self.learn and self.agent.ready():
            self.losses.append(self.agent.learn())

    def on_end(self, endedIds, status):
        # 이번 step에 끝난 패킷들 (도착, 목적지 기한 초과, 중간 기한 초과, TTL 만료)
        for packetId in endedIds:
            prev = self.pending.pop(int(packetId), None)
            if prev is None:
                continue
            pObs, pMask, pAction, pR = prev
            st = int(status[packetId])
            self._push(pObs, pAction, pR + self._terminal(int(packetId), st, status), self.zeroObs, 1.0, self.zeroMask)
            self.numEnded += 1

    def finish(self):
        # 에피소드 끝: 아직 안 끝난 패킷(maxDrainTime 초과)은 결과를 몰라서 버림
        dropped = len(self.pending)
        self.pending = {}
        return dropped

    def _terminal(self, packetId, st, status):
        # 연속 손실: 바로 앞 번호 패킷이 (지금까지) 손실이면 prevLost (팀원의 패킷 번호 기준으로 바꿀 예정)
        prevLost = packetId > 0 and int(status[packetId - 1]) in LOSS_STATUS
        return terminal_reward(st, self.RL, prevLost)

    def _push(self, obs, action, reward, nextObs, done, nextMask):
        self.agent.remember(obs, action, reward, nextObs, done, nextMask)
        self.numTransitions += 1
