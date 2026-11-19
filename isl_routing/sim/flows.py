# 주 흐름 여러 개 - 에피소드마다 실시간 UDP 흐름 목록(출발 위성, 도착 위성)과 흐름별 기한, TTL을 정함
#
# 흐름 0: GSL에서 넘어오는 주 흐름. 도착 = 격자 맨 끝 모서리 (P.dstSat, 회의 결정), 출발 = 에피소드 시드로 무작위
#   학습, 검증, 최종 평가 모두 같은 규칙 (시드가 같으면 같은 출발 -> B, C를 같은 조건에서 비교)
# 흐름 1 ~ numFlows-1: GSL이 모델링하지 않는 다른 지역 지상국의 흐름
#   출발, 도착 위성을 에피소드 시드로 무작위로 뽑음. 흐름마다 거리 구간이 다름 (P.flowDistBands, D = P.maxFlowDelay의 비율)
#   기본: 흐름 1 짧은 경로 (D의 0~1/3), 흐름 2 중간 (1/3~2/3), 흐름 3 긴 경로 (2/3~1). 6x6은 D = 45 ms
# 흐름마다 기한 = 최소 지연 + 여유, TTL = 최소 홉 + 여유 (sim/topology.flow_limits) -> P.mainDeadlines, P.mainTtls
# 에피소드(10초) 안에서는 고정 (위성 핸드오버는 몇 분 단위라 한 연결로 봄). 흐름마다 초당 P.genRate개
# 흐름끼리 출발 위성, 도착 위성이 겹치지 않게 뽑음 (흐름 0의 끝점은 흐름 1~의 도착으로 쓰지 않음)
import numpy as np

from routing.route_A import _dist_to
from sim.topology import flow_limits


def make_flows(P, G, seed):
    # 반환: [((출발 p, 출발 s), (도착 p, 도착 s)), ...] 길이 P.numFlows
    rng = np.random.RandomState(int(seed) + 300000)   # 배경 트래픽 난수와 다른 난수열
    end = (int(P.dstSat[0]), int(P.dstSat[1]))
    sats = [(p, s) for p in range(P.numPlanes) for s in range(P.satsPerPlane)]
    starts = [x for x in sats if x != end and flow_limits(P, G, x, end) is not None]   # 끝점까지 길이 있는 위성
    flows = [(starts[rng.randint(len(starts))], end)]
    numFlows = int(getattr(P, 'numFlows', 1))
    if numFlows <= 1:
        return flows
    D = P.maxFlowDelay
    bands = [(lo * D, hi * D) for lo, hi in P.flowDistBands]
    cands = [[] for _ in bands]                       # 구간별 (출발, 도착) 후보
    for dst in sats:
        dist = _dist_to(G, dst)
        for src in sats:
            if src == dst or not np.isfinite(dist[src]):
                continue
            for b, (lo, hi) in enumerate(bands):
                if lo < dist[src] <= hi:
                    cands[b].append((src, dst))
    for k in range(1, numFlows):
        b = (k - 1) % len(bands)
        if not cands[b]:
            raise ValueError(f'흐름 {k}: 최소 지연 {bands[b][0]:.0f}~{bands[b][1]:.0f} step 구간에 출발, 도착 쌍이 없습니다')
        for _ in range(100000):
            src, dst = cands[b][rng.randint(len(cands[b]))]
            if not any(src == a or dst == c for a, c in flows):   # 다른 흐름과 출발 위성이나 도착 위성이 겹치면 다시 뽑음
                flows.append((src, dst))
                break
        else:
            raise ValueError(f'흐름 {k}: 다른 흐름과 겹치지 않는 쌍을 찾지 못했습니다')
    return flows


def set_flow_limits(P, G):
    # P.mainFlows마다 기한, TTL을 정해 P.mainDeadlines, P.mainTtls에 넣음 (run_isl_sim이 패킷마다 씀)
    limits = [flow_limits(P, G, a, b) for a, b in P.mainFlows]
    P.mainDeadlines = [d for d, _ in limits]
    P.mainTtls = [t for _, t in limits]
    return P
