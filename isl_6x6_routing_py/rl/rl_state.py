# 관측 벡터(State 20개) C_RL이 방향을 고를 때 보는 상태 숫자 20개
#
# 학습 때(저장된 decision_log)와 실행 때(시뮬레이터 안)같은 상황이면 똑같은 숫자가 나와야 하므로
# 정규화는 normalize() 하나에서만 함
#
# 관측 벡터 순서 (방향 : 상, 하, 좌, 우)
#   0~3   큐 길이 q ÷ 200           (없는 방향은 0)
#   4~7   이웃 위성 부하 N ÷ 200     (없는 방향은 0)
#   8~11  링크 점유율 L (0~1)        (없는 방향은 0)
#   12~15 상하좌우 각 링크 유무 (1 - 있음, 0 - 격자 끝)
#   16~17 목적지까지 남은 거리 rem_dp, rem_ds ÷ 5 (목적지가 반대쪽이면 음수)
#   18    남은 기한 ÷ 70
#   19    남은 TTL ÷ 20

from dataclasses import dataclass

import numpy as np

from routing.A_Dijkstra import dist_to_dst
from sim.build_grid import build_grid

DIR_NAMES = ['up', 'down', 'left', 'right']
OBS_NAMES = ([f'q_{d}' for d in DIR_NAMES] + [f'N_{d}' for d in DIR_NAMES] + [f'L_{d}' for d in DIR_NAMES]
             + [f'link_{d}' for d in DIR_NAMES] + ['rem_dp', 'rem_ds', 'rem_deadline', 'ttl'])

# decision_log 열 번호 (sim/run_isl_sim.py 기록 순서)
#   t, packet_id, hop, p, s, q 4, L 4, N 4, rem_dp, rem_ds, rem_deadline, ttl, next_dir, choice_type, enqueued
COL_Q, COL_L, COL_N = slice(5, 9), slice(9, 13), slice(13, 17)
COL_REM_DP, COL_REM_DS, COL_REM_DEADLINE, COL_TTL = 17, 18, 19, 20


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


def normalize(q, N, L, remDp, remDs, remDeadline, ttl, RL):
    # 원래 값 -> 관측 벡터 20개 (없는 방향은 q = -1로 들어옴)
    q = np.asarray(q, dtype=float)
    link = (q >= 0).astype(float)
    obs = np.concatenate([
        np.where(link > 0, q / RL.normQueue, 0.0),
        np.where(link > 0, np.asarray(N, dtype=float) / RL.normQueue, 0.0),
        np.where(link > 0, np.asarray(L, dtype=float), 0.0),
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


def raw_from_sim(curP, curS, queueLen, G, P):
    # 시뮬레이터 상태 -> 4방향 q, N, L (B, D와 같은 계산식, 없는 방향은 -1)
    q = [-1.0] * 4
    N = [-1.0] * 4
    L = [-1.0] * 4
    for d in G.validDirs[curP][curS]:
        nextP = curP + G.stepP[d - 1]
        nextS = curS + G.stepS[d - 1]
        V = queueLen[G.linkId[curP, curS, d - 1]]
        q[d - 1] = float(V)
        N[d - 1] = float(np.mean(queueLen[G.outLinks[nextP][nextS]]))
        L[d - 1] = (P.k * V + (1 - P.k) * N[d - 1]) / P.queueMax
    return q, N, L


def obs_from_sim(curP, curS, queueLen, G, P, RL, remDeadline, ttl):
    # 실행용: 신경망 입력과 결정 기록용 원래 값을 이름 붙인 구조로 돌려준다.
    q, N, L = raw_from_sim(curP, curS, queueLen, G, P)
    obs = normalize(q, N, L, G.dstSat[0] - curP, G.dstSat[1] - curS, remDeadline, ttl, RL)
    mask = action_mask(q, P, G, curP, curS, remDeadline)
    return RoutingObservation(obs, mask.values, q, N, L, mask.deadlineFallback)


def obs_from_log(decisionLog, P, RL):
    # 학습용: decision_log 행들 (행 수 x 24) -> 관측 벡터 (행 수 x 20), 행동 마스크 (행 수 x 4)
    D = np.asarray(decisionLog, dtype=float)
    if D.size == 0:
        return np.empty((0, RL.obsDim), dtype=np.float32), np.empty((0, RL.numActions), dtype=np.float32)
    D = np.atleast_2d(D)
    obs = np.stack([normalize(r[COL_Q], r[COL_N], r[COL_L], r[COL_REM_DP], r[COL_REM_DS],
                              r[COL_REM_DEADLINE], r[COL_TTL], RL) for r in D])
    G = build_grid(P)
    mask = np.stack([action_mask(r[COL_Q], P, G, int(r[3]), int(r[4]), r[COL_REM_DEADLINE]).values for r in D])
    return obs, mask
