# 관측 벡터(State 24개) route_C가 방향을 고를 때 보는 상태 숫자 24개
#
# 같은 상황이면 항상 똑같은 숫자가 나와야 하므로 정규화는 normalize() 하나에서만 함
# 과거 값(큐 기록, 마지막 넘침 시각)은 시뮬레이터의 링크 기록(sim/link_history.py)에서 가져옴
#
# 관측 벡터 순서 (방향 : 상, 하, 좌, 우)
#   0~3   큐 길이 q ÷ 200                          (없는 방향은 0)
#   4~7   이웃 위성 부하 N ÷ 200                    (링크 지연만큼 늦게 받은 값: 좌우 2 step, 상하 7 step 전, 없는 방향은 0)
#   8~11  큐 증가 속도 (현재 - 10 step 전) ÷ 50, -1~1 (시작 10 step 동안 0, 없는 방향은 0)
#   12~15 최근 큐 넘침 min(지난 시간, 300) ÷ 300     (넘침 없으면 1, 없는 방향은 1)
#   16~19 상하좌우 각 링크 유무 (1 - 있음, 0 - 격자 끝)
#   20~21 목적지까지 남은 거리 rem_dp, rem_ds ÷ 5    (목적지가 반대쪽이면 음수)
#   22    남은 기한 ÷ 70
#   23    남은 TTL ÷ 20
#
# 링크 점유율 L은 큐 길이와 이웃 부하로 계산되는 중복 정보라 관측에서 뺐음 (decision_log 기록용으로만 계산)

from dataclasses import dataclass

import numpy as np

from routing.route_A import dist_to_dst
from sim.link_history import HISTORY_STEPS

DIR_NAMES = ['up', 'down', 'left', 'right']
OBS_NAMES = ([f'q_{d}' for d in DIR_NAMES] + [f'N_{d}' for d in DIR_NAMES] + [f'dq_{d}' for d in DIR_NAMES]
             + [f'overflow_{d}' for d in DIR_NAMES] + [f'link_{d}' for d in DIR_NAMES]
             + ['rem_dp', 'rem_ds', 'rem_deadline', 'ttl'])


@dataclass(frozen=True)
class ActionMask:
    values: np.ndarray
    deadlineFallback: bool


@dataclass(frozen=True)
class RoutingObservation:
    values: np.ndarray
    mask: np.ndarray
    queueLengths: list[float]
    neighborLoads: list[float]
    linkLoads: list[float]
    deadlineFallback: bool


def normalize(q, N, dq, sinceDrop, remDp, remDs, remDeadline, ttl, RL):
    # 원래 값 -> 관측 벡터 24개 (없는 방향은 q = -1로 들어옴)
    q = np.asarray(q, dtype=float)
    link = (q >= 0).astype(float)
    obs = np.concatenate([
        np.where(link > 0, q / RL.normQueue, 0.0),
        np.where(link > 0, np.asarray(N, dtype=float) / RL.normQueue, 0.0),
        np.where(link > 0, np.clip(np.asarray(dq, dtype=float) / RL.normDelta, -1.0, 1.0), 0.0),
        np.where(link > 0, np.minimum(np.asarray(sinceDrop, dtype=float), RL.overflowWindow) / RL.overflowWindow, 1.0),
        link,
        [remDp / RL.normDist, remDs / RL.normDist, remDeadline / RL.normDeadline, ttl / RL.normTtl],
    ])
    return obs.astype(np.float32)


def action_mask(q, P, G, curP, curS, remDeadline):
    # 링크/큐 조건과 기한 내 도착의 낙관적인 최소 지연을 함께 확인한다.
    # 모든 큐가 꽉 차거나 기한상 가능한 방향이 없으면 빈 마스크 대신 기존 후보로 되돌린다.
    q = np.asarray(q, dtype=float)
    link = q >= 0
    mask = link & (q < P.queueMax)
    if not mask.any():
        mask = link
    if not mask.any():
        raise ValueError(f'({curP}, {curS})에서 선택할 수 있는 링크가 없습니다')

    dist = dist_to_dst(G)
    feasible = np.zeros(4, dtype=bool)
    for d in np.flatnonzero(mask):
        nextP = int(curP + G.stepP[d])
        nextS = int(curS + G.stepS[d])
        linkId = G.linkId[int(curP), int(curS), d]
        lowerBound = G.linkDelay[linkId] + P.processingDelay + dist[nextP, nextS]
        feasible[d] = lowerBound <= remDeadline
    if feasible.any():
        return ActionMask(feasible.astype(np.float32), False)
    return ActionMask(mask.astype(np.float32), True)


def raw_from_sim(curP, curS, queueLen, G, P, RL, hist=None, t=0):
    # 시뮬레이터 상태 -> 4방향 원래 값 (없는 방향은 -1)
    #   q: 지금 큐 길이, N: 링크 지연만큼 늦게 받은 이웃 부하, dq: 큐 증가량, sinceDrop: 마지막 넘침 후 지난 step
    #   Lnow, Nnow: 지금 값으로 계산한 링크 점유율과 이웃 부하 (decision_log 기록용, A, B와 같은 계산식)
    # hist가 없으면 (테스트 등) 이웃 부하는 지금 값, 큐 증가량 0, 넘침 없음으로 둔다
    if RL.deltaWindow >= HISTORY_STEPS or max(P.linkDelay) >= HISTORY_STEPS:
        raise ValueError('링크 기록 길이(HISTORY_STEPS)가 관측에 필요한 과거보다 짧습니다')
    q, N, dq, sinceDrop, Lnow, Nnow = ([-1.0] * 4 for _ in range(6))
    for d in G.validDirs[curP][curS]:
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        link = G.linkId[curP, curS, d - 1]
        V = float(queueLen[link])
        q[d - 1] = V
        Nnow[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))
        Lnow[d - 1] = (P.k * V + (1 - P.k) * Nnow[d - 1]) / P.queueMax
        if hist is None:
            N[d - 1], dq[d - 1], sinceDrop[d - 1] = Nnow[d - 1], 0.0, float(RL.overflowWindow)
            continue
        past = hist.queue_at(t - int(G.linkDelay[link]))   # 이웃이 보낸 부하 정보는 링크 지연만큼 늦게 도착
        N[d - 1] = float(np.mean(past[G.outLinks[nextP][nextS]]))
        dq[d - 1] = V - float(hist.queue_at(t - RL.deltaWindow)[link]) if t > RL.deltaWindow else 0.0
        sinceDrop[d - 1] = float(t - hist.lastDrop[link])
    return q, N, dq, sinceDrop, Lnow, Nnow


def obs_from_sim(curP, curS, queueLen, G, P, RL, remDeadline, ttl, hist=None, t=0):
    # 실행용: 신경망 입력과 결정 기록용 원래 값을 이름 붙인 구조로 돌려준다.
    q, N, dq, sinceDrop, Lnow, Nnow = raw_from_sim(curP, curS, queueLen, G, P, RL, hist, t)
    obs = normalize(q, N, dq, sinceDrop, G.dstSat[0] - curP, G.dstSat[1] - curS, remDeadline, ttl, RL)
    mask = action_mask(q, P, G, curP, curS, remDeadline)
    return RoutingObservation(obs, mask.values, q, Nnow, Lnow, mask.deadlineFallback)
