# DQN 에이전트 - 신경망, 리플레이 버퍼, 행동 선택, 학습 함수
#
# 구조: 파라미터 공유 DQN (위성 36개가 신경망 하나를 같이 씀, 학습은 모든 위성 경험을 모아서)
#   신경망: 관측 20 -> 64 -> 64 -> 4 (방향별 Q값)
#   안정화: Double DQN, 타깃 신경망, 리플레이 버퍼, 행동 마스크 (없는 방향, 꽉 찬 큐는 고르지 않음)
#
# 경험 1개 = (obs, action, reward, next_obs, done, next_mask)
#   action: 0 상, 1 하, 2 좌, 3 우 (라우팅 방향 nextDir = action + 1)
#   done: 1이면 패킷이 끝남 (도착 또는 손실) -> 다음 상태 가치는 0
#   next_mask: 다음 위성에서 고를 수 있는 방향 (다음 상태의 최대 Q값을 구할 때 막힌 방향 제외)
import os

import numpy as np
import torch
import torch.nn as nn


class QNet(nn.Module):
    # 관측 벡터 -> 4방향 Q값
    def __init__(self, obsDim, numActions, hidden):
        super().__init__()
        layers = []
        size = obsDim
        for h in hidden:
            layers += [nn.Linear(size, h), nn.ReLU()]
            size = h
        layers.append(nn.Linear(size, numActions))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class ReplayBuffer:
    # 경험 창고: 꽉 차면 가장 오래된 경험부터 덮어씀, 학습 때 무작위로 꺼냄
    def __init__(self, size, obsDim, numActions, seed=0):
        self.size = size
        self.obs = np.zeros((size, obsDim), dtype=np.float32)
        self.act = np.zeros(size, dtype=np.int64)
        self.rew = np.zeros(size, dtype=np.float32)
        self.nextObs = np.zeros((size, obsDim), dtype=np.float32)
        self.done = np.zeros(size, dtype=np.float32)
        self.nextMask = np.zeros((size, numActions), dtype=np.float32)
        self.pos = 0
        self.count = 0
        self.rng = np.random.RandomState(seed)

    def push(self, obs, act, rew, nextObs, done, nextMask):
        i = self.pos
        self.obs[i] = obs
        self.act[i] = act
        self.rew[i] = rew
        self.nextObs[i] = nextObs
        self.done[i] = done
        self.nextMask[i] = nextMask
        self.pos = (self.pos + 1) % self.size
        self.count = min(self.count + 1, self.size)

    def sample(self, batchSize):
        idx = self.rng.randint(0, self.count, size=batchSize)
        return (self.obs[idx], self.act[idx], self.rew[idx], self.nextObs[idx], self.done[idx], self.nextMask[idx])

    def __len__(self):
        return self.count


class DQNAgent:
    def __init__(self, RL):
        self.RL = RL
        torch.manual_seed(RL.torchSeed)
        self.rng = np.random.RandomState(RL.torchSeed)
        self.q = QNet(RL.obsDim, RL.numActions, RL.hidden)            # 배우는 신경망
        self.qTarget = QNet(RL.obsDim, RL.numActions, RL.hidden)      # 정답 계산용 복사본 (가끔만 갱신)
        self.qTarget.load_state_dict(self.q.state_dict())
        self.opt = torch.optim.Adam(self.q.parameters(), lr=RL.lr)
        self.buffer = ReplayBuffer(RL.bufferSize, RL.obsDim, RL.numActions, RL.torchSeed)
        self.numDecisions = 0   # 지금까지 고른 횟수 (ε 줄이는 기준)
        self.numUpdates = 0     # 지금까지 학습한 횟수 (타깃 갱신 기준)

    # ---- 행동 선택 ----
    def epsilon(self):
        # ε: epsStart -> epsEnd로 epsDecaySteps 동안 직선으로 줄임
        frac = min(self.numDecisions / self.RL.epsDecaySteps, 1.0)
        return self.RL.epsStart + frac * (self.RL.epsEnd - self.RL.epsStart)

    def act(self, obs, mask, explore=True):
        # 관측, 마스크 -> 방향 번호 action (0 상, 1 하, 2 좌, 3 우)
        # explore=True(학습 중)면 ε 확률로 허용된 방향 중 무작위, 아니면 Q값이 가장 큰 허용 방향
        allowed = np.flatnonzero(mask)
        if explore:
            eps = self.epsilon()
            self.numDecisions += 1
            if self.rng.random_sample() < eps:
                return int(self.rng.choice(allowed))
        with torch.no_grad():
            qv = self.q(torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)).squeeze(0).numpy()
        qv = np.where(mask > 0, qv, -np.inf)
        return int(np.argmax(qv))

    # ---- 학습 ----
    def remember(self, obs, act, rew, nextObs, done, nextMask):
        self.buffer.push(obs, act, rew, nextObs, done, nextMask)

    def ready(self):
        # 경험이 learnStart만큼 쌓였고, 이번 결정이 trainEvery번째인지
        return len(self.buffer) >= self.RL.learnStart and self.numDecisions % self.RL.trainEvery == 0

    def learn(self):
        # 버퍼에서 batchSize개 꺼내 한 번 학습, 손실값(loss) 반환
        RL = self.RL
        obs, act, rew, nextObs, done, nextMask = (torch.as_tensor(x) for x in self.buffer.sample(RL.batchSize))

        qSa = self.q(obs).gather(1, act.unsqueeze(1)).squeeze(1)   # 지금 Q(s, a)

        with torch.no_grad():
            blocked = nextMask <= 0
            if RL.doubleDQN:
                # 배우는 신경망이 다음 방향을 고르고, 타깃 신경망이 그 방향의 점수를 매김
                nextA = self.q(nextObs).masked_fill(blocked, -1e9).argmax(1, keepdim=True)
                nextQ = self.qTarget(nextObs).gather(1, nextA).squeeze(1)
            else:
                nextQ = self.qTarget(nextObs).masked_fill(blocked, -1e9).max(1).values
            nextQ = torch.where(done > 0, torch.zeros_like(nextQ), nextQ)   # 끝난 패킷은 다음 가치 0
            target = rew + RL.gamma * nextQ                                 # Bellman: r + γ max Q(s', a')

        loss = nn.functional.smooth_l1_loss(qSa, target)   # Huber 손실 (큰 오차에 덜 민감)
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), RL.gradClip)
        self.opt.step()

        self.numUpdates += 1
        if self.numUpdates % RL.targetUpdate == 0:
            self.qTarget.load_state_dict(self.q.state_dict())
        return loss.item()

    # ---- 저장, 불러오기 ----
    def save(self, path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        torch.save({'q': self.q.state_dict(), 'qTarget': self.qTarget.state_dict(), 'opt': self.opt.state_dict(),
                    'numDecisions': self.numDecisions, 'numUpdates': self.numUpdates}, path)

    def load(self, path):
        ck = torch.load(path)
        self.q.load_state_dict(ck['q'])
        self.qTarget.load_state_dict(ck['qTarget'])
        self.opt.load_state_dict(ck['opt'])
        self.numDecisions = ck['numDecisions']
        self.numUpdates = ck['numUpdates']
