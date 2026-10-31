# 강화학습 라우팅 C_RL - 학습된 DQN 신경망으로 다음 방향을 고름 (A, B, D와 입력/출력이 같음)
#
# 쓰기 전에 set_agent()로 에이전트를 붙여야 함
#   학습 때: set_agent(agent, RL, explore=True)  -> ε 확률로 무작위 탐험 (train_rl.py)
#   평가 때: set_agent(agent, RL, explore=False) -> 항상 Q값이 가장 큰 방향
# 방금 고른 결정(관측, 마스크, 행동)은 STATE.last에 남겨 둠 -> 경험 연결 장치가 가져다 씀
from types import SimpleNamespace

from rl.rl_state import obs_from_sim

STATE = SimpleNamespace(agent=None, RL=None, explore=False, last=None, collector=None, infeasibleMasks=0)


def set_agent(agent, RL, explore=False, collector=None):
    # collector: 학습 때 경험 연결 장치 (rl_collector.Collector), 평가 때는 None
    STATE.agent = agent
    STATE.RL = RL
    STATE.explore = explore
    STATE.last = None
    STATE.collector = collector
    STATE.infeasibleMasks = 0


def C_RL(curP, curS, queueLen, G, P, t=0, remDeadline=None, ttl=None, hops=None, **packet):
    # 입력: 현재 위성 (curP,curS), 링크별 큐 길이 queueLen, 그리드 G, 설정 P, 남은 기한 remDeadline, 남은 TTL ttl
    # 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우)
    #       choiceType 1 주 경로, 2 대체 경로, 3 그 외 방향 (B와 같은 기준, 결과 비교용)
    #       L, N 4방향 링크 점유율 / 이웃 부하 (없는 방향은 -1)
    if STATE.agent is None:
        raise RuntimeError('C_RL: set_agent()로 에이전트를 먼저 붙여야 함')

    observed = obs_from_sim(curP, curS, queueLen, G, P, STATE.RL, remDeadline, ttl)
    STATE.infeasibleMasks += int(observed.deadlineFallback)
    action = STATE.agent.act(observed.values, observed.mask, explore=STATE.explore)   # 0 상, 1 하, 2 좌, 3 우
    nextDir = action + 1
    STATE.last = (observed.values, observed.mask, action)

    # 주 경로 = 목적지 쪽 좌/우, 대체 경로 = 목적지 쪽 상/하 (B와 같은 기준)
    remainP = G.dstSat[0] - curP
    remainS = G.dstSat[1] - curS
    primaryDir = (3 + (remainP > 0)) if remainP != 0 else (1 + (remainS > 0))
    altDir = (1 + (remainS > 0)) if (remainP != 0 and remainS != 0) else 0
    choiceType = 1 if nextDir == primaryDir else 2 if nextDir == altDir else 3
    return nextDir, choiceType, observed.linkLoads, observed.neighborLoads
