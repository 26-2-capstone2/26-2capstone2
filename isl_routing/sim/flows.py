# 주 흐름 여러 개 - 에피소드마다 실시간 UDP 흐름 목록(출발 위성, 도착 위성)을 정함
#
# 흐름 0: 기존 주 흐름 P.srcSat -> P.dstSat (지금까지 결과와 비교, 나중에 GSL에서 넘어오는 흐름으로 씀)
# 흐름 1 ~ numFlows-1: GSL이 모델링하지 않는 다른 지역 지상국의 흐름
#   출발, 도착 위성을 에피소드 시드로 무작위로 뽑음 (같은 시드면 같은 흐름 -> B, C를 같은 조건에서 비교)
#   조건: 출발 -> 도착 최소 지연(링크 지연 합)이 P.flowDelayMin ~ P.flowDelayMax step (기한 여유를 주 흐름과 비슷하게)
#   에피소드(10초) 안에서는 고정 (위성 핸드오버는 몇 분 단위라 한 연결로 봄)
# 흐름마다 초당 P.genRate개 (GSL 세션 하나와 같은 값)
# P.flowZeroRandom = True (학습 때만): 흐름 0도 무작위로 뽑음 -> 특정 경로에 맞춰 배우지 않게.
#   검증, 최종 평가는 False로 두어 흐름 0을 (0,0) -> (5,5)로 고정 (테스트 1~5와 같은 경로로 비교)
# 흐름끼리 출발 위성, 도착 위성이 겹치지 않게 뽑음 (서로 너무 가까운 흐름 방지)
import numpy as np

from routing.route_A import _dist_to


def make_flows(P, G, seed):
    # 반환: [((출발 p, 출발 s), (도착 p, 도착 s)), ...] 길이 P.numFlows
    flows = [((int(P.srcSat[0]), int(P.srcSat[1])), (int(P.dstSat[0]), int(P.dstSat[1])))]
    numFlows = int(getattr(P, 'numFlows', 1))
    zeroRandom = bool(getattr(P, 'flowZeroRandom', False))
    if numFlows <= 1 and not zeroRandom:
        return flows
    if zeroRandom:
        flows = []
    rng = np.random.RandomState(int(seed) + 300000)   # 배경 트래픽 난수와 다른 난수열 (흐름 1개일 때 기존 결과가 그대로 나오게)
    sats = [(p, s) for p in range(P.numPlanes) for s in range(P.satsPerPlane)]
    cands = []
    for dst in sats:
        dist = _dist_to(G, dst)
        for src in sats:
            if src != dst and P.flowDelayMin <= dist[src] <= P.flowDelayMax:
                cands.append((src, dst))
    if not cands:
        raise ValueError(f'최소 지연 {P.flowDelayMin}~{P.flowDelayMax} step을 만족하는 출발, 도착 쌍이 없습니다')
    for _ in range(100000):
        if len(flows) >= max(numFlows, 1):
            break
        src, dst = cands[rng.randint(len(cands))]
        if any(src == a or dst == b for a, b in flows):   # 다른 흐름과 출발 위성이나 도착 위성이 겹치면 다시 뽑음
            continue
        flows.append((src, dst))
    else:
        raise ValueError('서로 겹치지 않는 흐름을 만들지 못했습니다')
    return flows
