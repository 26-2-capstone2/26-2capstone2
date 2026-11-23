# 변수 설정 화면의 칸 목록 - 화면 칸 하나 = 코드 변수 하나 (config_isl.py, config_rl.py)
#
# 기본값은 항상 config_isl(), config_rl()에서 읽고, 화면에서 바꾼 값(overrides)만 그 위에 덮어씀
# -> 설정 파일의 확정값 자체는 바꾸지 않음
#
# kind: int, float, pair(칸 2개), ratio(글자 'b:h:s'), bool, select(목록에서 고름), fixed(바꿀 수 없음)
# 망 구조는 4개 중에서만 고름 (아무 크기나 허용하면 큰 망에서 에피소드 준비가 수십 초씩 걸림)
# 배경 트래픽은 지역 핫스팟 방식(P.bgMode = 'event')만 다룸 (옛 hotspot 방식은 웹에서 뺌)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing

from config_isl import EVENT_LEVELS, config_isl
from sim.topology import apply_topology, link_delay_steps, link_enabled, update_limits
from rl.config_rl import apply_level_ratio, config_rl

LEVELS = list(EVENT_LEVELS)
TOPOLOGIES = [('iridium', '이리듐 6 x 11'), ('starlink:20x20', '스타링크 20 x 20'),
              ('starlink:36x36', '스타링크 36 x 36'), ('starlink', '스타링크 72 x 22')]
DEFAULT_TOPOLOGY = 'iridium'
TOPO_NAME = dict(TOPOLOGIES)


def _delay_range(P):
    # 실제 위성군 링크 지연은 거리로 계산 -> 가장 짧은 ~ 가장 긴 값
    d = [link_delay_steps(P, s, k) for s in range(P.satsPerPlane) for k in (1, 3) if link_enabled(P, 0, s, k)]
    return f'{min(d)} ~ {max(d)} ms (거리로 계산)'


def level_ratio(RL):
    # 학습 단계 비율 -> 'b:h:s' (예 '0:1:2'). cycle 방식이면 들어 있는 단계를 1로
    if getattr(RL, 'trainLevelMode', 'cycle') == 'weighted':
        w = RL.trainLevelWeights
    else:
        w = {lv: 1 for lv in RL.trainLevels}
    return ':'.join(f'{w.get(lv, 0):g}' for lv in LEVELS)


def _pair(a, b, cast):
    # pair 칸 쓰기: P.a, P.b = v[0], v[1]
    def setter(obj, v):
        setattr(obj, a, cast(v[0]))
        setattr(obj, b, cast(v[1]))
    return setter


def _set(name, cast):
    return lambda obj, v: setattr(obj, name, cast(v))


def _get(name):
    return lambda P, RL: getattr(P, name)


def _getr(name):
    return lambda P, RL: getattr(RL, name)


BG = '배경 트래픽 (지역 핫스팟)'

# (key, 묶음, 왼쪽/오른쪽, 이름, 단위, 종류, 읽기, 쓰기)
FIELDS = [
    # ---- 왼쪽: 시뮬레이터 (config_isl.py) ----
    ('topology', '네트워크', 'left', '망 구조', '', 'select', _get('topoName'), None),
    ('sats', '네트워크', 'left', '위성 수', '궤도면 x 궤도면당 위성', 'fixed', lambda P, RL: f'{P.numPlanes * P.satsPerPlane} ({P.numPlanes} x {P.satsPerPlane})', None),
    ('polarLat', '네트워크', 'left', '극지방 옆 궤도 링크', '이 위도 이상에서 꺼짐', 'fixed',
     lambda P, RL: f'위도 {P.polarLatLimitDeg:g}도' if P.polarLatLimitDeg else '항상 켜짐', None),
    ('queueMax', '네트워크', 'left', '링크 큐 크기', '개', 'int', _get('queueMax'), _set('queueMax', int)),
    ('linkCapacity', '네트워크', 'left', '링크 전송량', '개 / ms', 'int', _get('linkCapacity'), _set('linkCapacity', int)),
    ('linkDelay', '네트워크', 'left', '링크 지연', '같은 궤도, 옆 궤도', 'fixed', lambda P, RL: _delay_range(P), None),
    ('processingDelay', '네트워크', 'left', '처리 지연', 'ms', 'int', _get('processingDelay'), _set('processingDelay', int)),
    ('numFlows', '주 흐름', 'left', '흐름 수', '개', 'int', _get('numFlows'), _set('numFlows', int)),
    ('dstSat', '주 흐름', 'left', '흐름 0 도착', '끝점 위성, 출발은 시드로 무작위', 'fixed', lambda P, RL: f'({P.dstSat[0]}, {P.dstSat[1]})', None),
    ('flowDistBands', '주 흐름', 'left', '흐름 1, 2, 3 거리 구간', 'D의 비율 (D = 끝점까지 가장 먼 거리)', 'fixed',
     lambda P, RL: ', '.join(f'{lo * P.maxFlowDelay:.0f}~{hi * P.maxFlowDelay:.0f} ms' for lo, hi in P.flowDistBands), None),
    ('deadlineMargin', '패킷', 'left', '기한 여유 (흐름 최소 지연 +)', 'ms', 'int', _get('deadlineMargin'), _set('deadlineMargin', int)),
    ('ttlMargin', '패킷', 'left', 'TTL 여유 (흐름 최소 홉 +)', '홉', 'int', _get('ttlMargin'), _set('ttlMargin', int)),
    ('deadline', '패킷', 'left', '가장 먼 흐름 0 기한', 'ms, 자동 계산', 'fixed', _get('deadline'), None),
    ('genRate', '패킷', 'left', '흐름마다 초당 패킷', '개', 'int', _get('genRate'), _set('genRate', int)),
    ('packetSize', '패킷', 'left', '패킷 크기', 'Byte', 'int', _get('packetSize'), _set('packetSize', int)),
    ('burstMinLen', '패킷', 'left', '연속 손실 기준', '개 이상', 'int', _get('burstMinLen'), _set('burstMinLen', int)),
    ('bgBase', BG, 'left', '기본 부하 (링크 용량 대비)', '배', 'pair', lambda P, RL: [P.bgBaseMin, P.bgBaseMax], _pair('bgBaseMin', 'bgBaseMax', float)),
    ('evLoad', BG, 'left', '핫스팟 세기 (기본 부하에 더함)', '배', 'pair', lambda P, RL: [P.evLoadMin, P.evLoadMax], _pair('evLoadMin', 'evLoadMax', float)),
    ('evNbrRatio', BG, 'left', '이웃 위성 세기 비율', '배', 'float', _get('evNbrRatio'), _set('evNbrRatio', float)),
    ('evCorridor', BG, 'left', '주 흐름 지역 폭', '칸', 'float', _get('evCorridor'), _set('evCorridor', float)),
    ('bgRelWeight', BG, 'left', '주 흐름 지역 가중치', '배', 'float', _get('bgRelWeight'), _set('bgRelWeight', float)),
    ('evSafeLoad', BG, 'left', '우회 길 확인 기준', '배', 'float', _get('evSafeLoad'), _set('evSafeLoad', float)),
    ('evRefSats', BG, 'left', '핫스팟 빈도 기준', '위성 수에 비례해 더 자주', 'fixed',
     lambda P, RL: f'위성 {P.evRefSats}개 기준, 지금 {P.numPlanes * P.satsPerPlane / P.evRefSats:.1f}배', None),
    ('bgTtl', BG, 'left', '배경 패킷 TTL', '홉', 'int', _get('bgTtl'), _set('bgTtl', int)),
    ('simTime', '실험 (평가)', 'left', '에피소드 길이', '초', 'float', lambda P, RL: P.simTime / 1000,
     lambda P, v: setattr(P, 'simTime', int(float(v) * 1000))),
    ('maxDrainTime', '실험 (평가)', 'left', '남은 패킷 처리 시간', 'ms', 'int', _get('maxDrainTime'), _set('maxDrainTime', int)),
    ('numEpisodes', '실험 (평가)', 'left', '평가 에피소드 수', '개', 'int', _get('numEpisodes'), _set('numEpisodes', int)),
    ('evalSeeds', '실험 (평가)', 'left', '평가 시드', '학습에 쓰지 않음', 'fixed', lambda P, RL: '1 ~ 20', None),
    # ---- 오른쪽: 강화학습 (config_rl.py) ----
    ('obsDim', '에이전트 구조', 'right', '관측 숫자', '큐 4, 이웃 4, 링크 4, 거리 2, 기한 1, 큐 증가 속도 4, 최근 넘침 4', 'fixed', _getr('obsDim'), None),
    ('numActions', '에이전트 구조', 'right', '행동 (상, 하, 좌, 우)', '개', 'fixed', _getr('numActions'), None),
    ('maskMode', '에이전트 구조', 'right', '막는 방향', '링크 없는 방향 + 들어온 링크', 'fixed', _getr('maskMode'), None),
    ('hidden', '에이전트 구조', 'right', '신경망 중간층', '개', 'pair', lambda P, RL: list(RL.hidden),
     lambda RL, v: setattr(RL, 'hidden', [int(x) for x in v])),
    ('doubleDQN', '에이전트 구조', 'right', 'Double DQN', '', 'bool', _getr('doubleDQN'), _set('doubleDQN', bool)),
    ('rewardOnTime', '보상', 'right', '기한 내 도착', '', 'float', _getr('rewardOnTime'), _set('rewardOnTime', float)),
    ('rewardSingleLoss', '보상', 'right', '단발 손실 (1~2개)', '', 'float', _getr('rewardSingleLoss'), _set('rewardSingleLoss', float)),
    ('burstBase', '보상', 'right', '연속 손실 기본 벌점', '', 'float', _getr('burstBase'), _set('burstBase', float)),
    ('burstStep', '보상', 'right', '연속 손실 증가폭', '개마다', 'float', _getr('burstStep'), _set('burstStep', float)),
    ('burstMax', '보상', 'right', '연속 손실 최대 벌점', '', 'float', _getr('burstMax'), _set('burstMax', float)),
    ('burstStartPenalty', '보상', 'right', '연속 손실 시작 벌점', '3번째 손실에 한 번', 'float', _getr('burstStartPenalty'), _set('burstStartPenalty', float)),
    ('burstEnabled', '보상', 'right', '연속 손실 보상', '끄면 단발 손실과 같게 (대조 실험)', 'bool', _getr('burstEnabled'), _set('burstEnabled', bool)),
    ('rewardHopQueue', '보상', 'right', '홉 보상에 큐 포함', '끄면 링크 지연 ÷ 기한만', 'bool', _getr('rewardHopQueue'), _set('rewardHopQueue', bool)),
    ('rewardHopScale', '보상', 'right', '홉 보상 나눔값', '= 기한', 'fixed', _getr('rewardHopScale'), None),
    ('lr', 'DQN 학습', 'right', '학습률 (Adam)', '', 'float', _getr('lr'), _set('lr', float)),
    ('gamma', 'DQN 학습', 'right', '할인율 γ', '', 'float', _getr('gamma'), _set('gamma', float)),
    ('bufferSize', 'DQN 학습', 'right', '경험 버퍼 크기', '장', 'int', _getr('bufferSize'), _set('bufferSize', int)),
    ('batchSize', 'DQN 학습', 'right', '한 번에 꺼내는 수', '장', 'int', _getr('batchSize'), _set('batchSize', int)),
    ('learnStart', 'DQN 학습', 'right', '학습 시작 (흐름 수 비례)', '장 이후', 'int', _getr('learnStart'), _set('learnStart', int)),
    ('trainEvery', 'DQN 학습', 'right', '학습 주기 (흐름 수 비례)', '번 결정마다', 'int', _getr('trainEvery'), _set('trainEvery', int)),
    ('targetUpdate', 'DQN 학습', 'right', '타깃 신경망 갱신', '번 학습마다', 'int', _getr('targetUpdate'), _set('targetUpdate', int)),
    ('tau', 'DQN 학습', 'right', '타깃 섞는 비율 τ', '0이면 통째로 복사', 'float', _getr('tau'), _set('tau', float)),
    ('gradClip', 'DQN 학습', 'right', '기울기 최대 크기', '', 'float', _getr('gradClip'), _set('gradClip', float)),
    ('eps', '탐험 (ε-greedy)', 'right', 'ε 시작, 끝', '', 'pair', lambda P, RL: [RL.epsStart, RL.epsEnd], _pair('epsStart', 'epsEnd', float)),
    ('epsDecaySteps', '탐험 (ε-greedy)', 'right', 'ε 줄이는 기간 (흐름 수 비례)', '번 결정', 'int', _getr('epsDecaySteps'), _set('epsDecaySteps', int)),
    ('levelRatio', '학습 실행', 'right', '혼잡 단계 비율', 'base : high : severe', 'ratio', lambda P, RL: level_ratio(RL), apply_level_ratio),
    ('trainEpisodes', '학습 실행', 'right', '학습 에피소드 수', '개', 'int', _getr('trainEpisodes'), _set('trainEpisodes', int)),
    ('trainSeedStart', '학습 실행', 'right', '학습 시드 시작', '', 'int', _getr('trainSeedStart'), _set('trainSeedStart', int)),
    ('saveEvery', '학습 실행', 'right', '중간 저장 주기', '에피소드', 'int', _getr('saveEvery'), _set('saveEvery', int)),
    ('torchSeed', '학습 실행', 'right', '신경망 시드', '', 'int', _getr('torchSeed'), _set('torchSeed', int)),
    ('evalEvery', '검증 평가 (학습 중)', 'right', '검증 주기 (0이면 안 함)', '에피소드마다', 'int', _getr('evalEvery'), _set('evalEvery', int)),
    ('valSeeds', '검증 평가 (학습 중)', 'right', '검증 시드', 'ε 0, 학습 없음', 'fixed', lambda P, RL: f'{RL.valSeeds[0]} ~ {RL.valSeeds[-1]}', None),
]
P_KEYS = {f[0] for f in FIELDS if f[2] == 'left'}


def build_config(overrides=None):
    # 기본 설정 + 화면에서 바꾼 값 -> (P, RL)
    # 순서: P 덮어쓰기 -> 끝점, 기한, TTL 다시 계산 -> config_rl(P) (기한, 흐름 수 등 P에서 따라오는 값 반영) -> RL 덮어쓰기
    overrides = overrides or {}
    P = config_isl()
    P.nodeLogEnable = False
    P.bgMode = 'event'
    P.topoName = overrides.get('topology', DEFAULT_TOPOLOGY)
    if P.topoName not in TOPO_NAME:
        raise ValueError(f'망 구조는 {list(TOPO_NAME)} 중 하나: {P.topoName}')
    apply_topology(P, P.topoName, limits=False)   # 끝점, 기한은 아래 update_limits에서 한 번만
    for key, _, side, _, _, kind, _, setter in FIELDS:
        if side == 'left' and setter and key in overrides:
            setter(P, overrides[key])
    update_limits(P)                   # 망 구조, 여유를 바꿨으면 끝점, 기한, TTL이 따라 바뀜
    RL = config_rl(P)
    for key, _, side, _, _, kind, _, setter in FIELDS:
        if side == 'right' and setter and key in overrides:
            setter(RL, overrides[key])
    return P, RL


def describe(overrides=None):
    # 화면에 보낼 칸 목록: 기본값(default)과 지금 값(value)을 같이
    P0, RL0 = build_config({})
    P, RL = build_config(overrides) if overrides else (P0, RL0)
    out = []
    for key, group, side, label, unit, kind, getter, _ in FIELDS:
        item = dict(key=key, group=group, side=side, label=label, unit=unit, kind=kind,
                    default=getter(P0, RL0), value=getter(P, RL))
        if kind == 'select':
            item['options'] = [dict(value=v, label=l) for v, l in TOPOLOGIES]
        if key == 'levelRatio':   # 단계별 지역 핫스팟 발생 간격, 지속 (ms = step)
            item['table'] = {k: v for k, v in EVENT_LEVELS.items()}
        out.append(item)
    return out


def map_data(P, G):
    # 2D 지도용 망 모양: 위성 [경도, 위도] (번호 = p x 궤도면당 위성 수 + s), 링크 쌍 [위성 a, 위성 b]
    # pairOf: 방향 링크(validDirs 순서)마다 몇 번째 쌍인지 (양방향 큐 중 큰 값을 지도에 칠함)
    from sim.topology import sat_lonlat
    S = P.satsPerPlane
    pairs, idx, linkIds, pairOf = [], {}, [], []
    for p in range(P.numPlanes):
        for s in range(S):
            for d in G.validDirs[p][s]:
                a, b = p * S + s, int(G.nbrP[p, s, d - 1]) * S + int(G.nbrS[p, s, d - 1])
                key = (min(a, b), max(a, b))
                if key not in idx:
                    idx[key] = len(pairs)
                    pairs.append([a, b])
                linkIds.append(int(G.linkId[p, s, d - 1]))
                pairOf.append(idx[key])
    view = dict(topology=getattr(P, 'topoName', P.topology), name=TOPO_NAME.get(getattr(P, 'topoName', ''), P.topology),
                planes=P.numPlanes, sats=S, geo=sat_lonlat(P), pairs=pairs, polar=P.polarLatLimitDeg)
    return view, linkIds, pairOf


_VIEW_CACHE = {}


def topology_view(overrides):
    # 시뮬레이터 대기 화면, 메인 화면 지도 미리보기: 망 모양 + 실행 조건 요약 (같은 설정이면 다시 계산 안 함)
    import json
    from sim.build_grid import build_grid
    key = json.dumps(overrides, sort_keys=True)
    if key not in _VIEW_CACHE:
        P, RL = build_config(overrides)
        view, _, _ = map_data(P, build_grid(P))
        n = P.numPlanes * P.satsPerPlane
        view['info'] = dict(numSats=n, dst=[int(P.dstSat[0]), int(P.dstSat[1])], maxFlowDelay=int(P.maxFlowDelay),
                            deadline=int(P.deadline), deadlineMargin=P.deadlineMargin, genRate=P.genRate, numFlows=P.numFlows,
                            hotRatio=round(n / P.evRefSats, 1), levelRatio=level_ratio(RL), trainEpisodes=RL.trainEpisodes,
                            evalEvery=RL.evalEvery, simTime=P.simTime / 1000, obsDim=RL.obsDim, lr=RL.lr, gamma=RL.gamma,
                            epsStart=RL.epsStart, epsEnd=RL.epsEnd, burstStartPenalty=RL.burstStartPenalty,
                            delay=_delay_range(P), polar=P.polarLatLimitDeg, wrap=[P.wrapP, P.wrapS])
        _VIEW_CACHE.clear() if len(_VIEW_CACHE) > 20 else None
        _VIEW_CACHE[key] = view
    return _VIEW_CACHE[key]
