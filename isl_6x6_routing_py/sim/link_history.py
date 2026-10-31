# 링크별 최근 기록 - route_C의 관측(State)에 쓰는 과거 값
#   큐 길이 기록: 최근 HISTORY_STEPS step의 링크별 큐 길이 (큐 증가 속도, 링크 지연만큼 늦게 받는 이웃 부하에 사용)
#   마지막 넘침 시각: 링크 큐에서 패킷(주 흐름, 배경 모두)이 버려진 마지막 step
# 시뮬레이터(sim/run_isl_sim.py)가 매 step 끝에 record(), 큐가 넘칠 때 drop()을 부름
import numpy as np

HISTORY_STEPS = 32   # 큐 증가 속도 10 step, 이웃 부하 지연 최대 7 step보다 넉넉하게
NEVER = -10 ** 9     # 한 번도 넘친 적 없음


class LinkHistory:
    def __init__(self, numLinks):
        self.queue = np.zeros((HISTORY_STEPS, numLinks), dtype=np.int64)   # 시작 전 큐는 모두 비어 있음
        self.lastDrop = np.full(numLinks, NEVER, dtype=np.int64)

    def record(self, t, queueLen):
        # step t가 끝났을 때의 큐 길이
        self.queue[t % HISTORY_STEPS] = queueLen

    def drop(self, link, t):
        self.lastDrop[link] = t

    def queue_at(self, t):
        # step t가 끝났을 때의 큐 길이 (t <= 0이면 시작 전 상태)
        if t <= 0:
            return np.zeros(self.queue.shape[1], dtype=np.int64)
        return self.queue[t % HISTORY_STEPS]
