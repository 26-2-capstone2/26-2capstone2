# 변수 설정 화면의 칸 목록 - 화면 칸 하나 = 코드 변수 하나 (config_isl.py, config_rl.py)
#
# 기본값은 항상 config_isl(), config_rl()에서 읽고, 화면에서 바꾼 값(overrides)만 그 위에 덮어씀
# -> 설정 파일의 확정값 자체는 바꾸지 않음
#
# kind: int, float, pair(칸 2개), ratio(글자 'b:h:s'), bool, fixed(바꿀 수 없음)
# 배경 트래픽은 지역 핫스팟 방식(P.bgMode = 'event')만 다룸 (옛 hotspot 방식은 웹에서 뺌)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing

from config_isl import EVENT_LEVELS, config_isl
from rl.config_rl import config_rl

LEVELS = list(EVENT_LEVELS)


def _set_delay(P, v):
    ud, lr = v
    P.linkDelay[:] = [ud, ud, lr, lr]


def level_ratio(RL):
    # 학습 단계 비율 -> 'b:h:s' (예 '0:1:2'). cycle 방식이면 들어 있는 단계를 1로
    if getattr(RL, 'trainLevelMode', 'cycle') == 'weighted':
        w = RL.trainLevelWeights
    else:
        w = {lv: 1 for lv in RL.trainLevels}
    return ':'.join(f'{w.get(lv, 0):g}' for lv in LEVELS)


def apply_level_ratio(RL, ratio):
    # rl/train_rl.py의 apply_level_ratio와 같음 (그 파일은 PyTorch를 불러와서 여기서 따로 씀). 0인 단계는 학습과 검증에서 뺌
    w = [float(x) for x in str(ratio).split(':')]
    if len(w) != 3 or min(w) < 0 or sum(w) <= 0:
        raise ValueError(f'혼잡 단계 비율은 base:high:severe 형식 (예 0:1:2): {ratio}')
    RL.trainLevelMode = 'weighted'
    RL.trainLevels = [lv for lv, x in zip(LEVELS, w) if x > 0]
    RL.trainLevelWeights = {lv: x for lv, x in zip(LEVELS, w) if x > 0}
    RL.valLevels = list(RL.trainLevels)
    return RL


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
    ('numPlanes', '네트워크', 'left', '궤도면 수 (좌우)', '개', 'int', _get('numPlanes'), _set('numPlanes', int)),
    ('satsPerPlane', '네트워크', 'left', '궤도면당 위성 수 (상하)', '개', 'int', _get('satsPerPlane'), _set('satsPerPlane', int)),
    ('queueMax', '네트워크', 'left', '링크 큐 크기', '개', 'int', _get('queueMax'), _set('queueMax', int)),
    ('linkCapacity', '네트워크', 'left', '링크 전송량', '개 / ms', 'int', _get('linkCapacity'), _set('linkCapacity', int)),
    ('linkDelay', '네트워크', 'left', '링크 지연 (상하, 좌우)', 'ms', 'pair', lambda P, RL: [int(P.linkDelay[0]), int(P.linkDelay[2])],
     lambda P, v: _set_delay(P, [int(x) for x in v])),
    ('processingDelay', '네트워크', 'left', '처리 지연', 'ms', 'int', _get('processingDelay'), _set('processingDelay', int)),
    ('numFlows', '주 흐름', 'left', '흐름 수', '개', 'int', _get('numFlows'), _set('numFlows', int)),
    ('srcSat', '주 흐름', 'left', '흐름 0 출발 (검증, 평가)', '', 'pair', lambda P, RL: [int(x) for x in P.srcSat],
     lambda P, v: P.srcSat.__setitem__(slice(None), [int(x) for x in v])),
    ('dstSat', '주 흐름', 'left', '흐름 0 도착 (검증, 평가)', '', 'pair', lambda P, RL: [int(x) for x in P.dstSat],
     lambda P, v: P.dstSat.__setitem__(slice(None), [int(x) for x in v])),
    ('flowDelay', '주 흐름', 'left', '무작위 흐름 최소 지연', 'ms', 'pair', lambda P, RL: [P.flowDelayMin, P.flowDelayMax],
     _pair('flowDelayMin', 'flowDelayMax', int)),
    ('deadline', '패킷', 'left', '기한', 'ms', 'int', _get('deadline'), _set('deadline', int)),
    ('ttlInit', '패킷', 'left', 'TTL', '홉', 'int', _get('ttlInit'), _set('ttlInit', int)),
    ('genRate', '패킷', 'left', '흐름마다 초당 패킷', '개', 'int', _get('genRate'), _set('genRate', int)),
    ('packetSize', '패킷', 'left', '패킷 크기', 'Byte', 'int', _get('packetSize'), _set('packetSize', int)),
    ('burstMinLen', '패킷', 'left', '연속 손실 기준', '개 이상', 'int', _get('burstMinLen'), _set('burstMinLen', int)),
    ('bgBase', BG, 'left', '기본 부하 (링크 용량 대비)', '배', 'pair', lambda P, RL: [P.bgBaseMin, P.bgBaseMax], _pair('bgBaseMin', 'bgBaseMax', float)),
    ('evLoad', BG, 'left', '핫스팟 세기 (기본 부하에 더함)', '배', 'pair', lambda P, RL: [P.evLoadMin, P.evLoadMax], _pair('evLoadMin', 'evLoadMax', float)),
    ('evNbrRatio', BG, 'left', '이웃 위성 세기 비율', '배', 'float', _get('evNbrRatio'), _set('evNbrRatio', float)),
    ('evCorridor', BG, 'left', '주 흐름 지역 폭', '칸', 'float', _get('evCorridor'), _set('evCorridor', float)),
    ('bgRelWeight', BG, 'left', '주 흐름 지역 가중치', '배', 'float', _get('bgRelWeight'), _set('bgRelWeight', float)),
    ('evSafeLoad', BG, 'left', '우회 길 확인 기준', '배', 'float', _get('evSafeLoad'), _set('evSafeLoad', float)),
    ('bgTtl', BG, 'left', '배경 패킷 TTL', '홉', 'int', _get('bgTtl'), _set('bgTtl', int)),
    ('simTime', '실험 (평가)', 'left', '에피소드 길이', '초', 'float', lambda P, RL: P.simTime / 1000,
     lambda P, v: setattr(P, 'simTime', int(float(v) * 1000))),
    ('maxDrainTime', '실험 (평가)', 'left', '남은 패킷 처리 시간', 'ms', 'int', _get('maxDrainTime'), _set('maxDrainTime', int)),
    ('numEpisodes', '실험 (평가)', 'left', '평가 에피소드 수', '개', 'int', _get('numEpisodes'), _set('numEpisodes', int)),
    ('evalSeeds', '실험 (평가)', 'left', '평가 시드', '학습에 쓰지 않음', 'fixed', lambda P, RL: '1 ~ 20', None),
    # ---- 오른쪽: 강화학습 (config_rl.py) ----
    ('obsDim', '에이전트 구조', 'right', '관측 숫자', '큐 4, 이웃 4, 링크 4, 거리 2, 기한 1', 'fixed', _getr('obsDim'), None),
    ('numActions', '에이전트 구조', 'right', '행동 (상, 하, 좌, 우)', '개', 'fixed', _getr('numActions'), None),
    ('maskMode', '에이전트 구조', 'right', '막는 방향', '링크 없는 방향만', 'fixed', _getr('maskMode'), None),
    ('hidden', '에이전트 구조', 'right', '신경망 중간층', '개', 'pair', lambda P, RL: list(RL.hidden),
     lambda RL, v: setattr(RL, 'hidden', [int(x) for x in v])),
    ('doubleDQN', '에이전트 구조', 'right', 'Double DQN', '', 'bool', _getr('doubleDQN'), _set('doubleDQN', bool)),
    ('rewardOnTime', '보상', 'right', '기한 내 도착', '', 'float', _getr('rewardOnTime'), _set('rewardOnTime', float)),
    ('rewardSingleLoss', '보상', 'right', '단발 손실 (1~2개)', '', 'float', _getr('rewardSingleLoss'), _set('rewardSingleLoss', float)),
    ('burstBase', '보상', 'right', '연속 손실 기본 벌점', '', 'float', _getr('burstBase'), _set('burstBase', float)),
    ('burstStep', '보상', 'right', '연속 손실 증가폭', '개마다', 'float', _getr('burstStep'), _set('burstStep', float)),
    ('burstMax', '보상', 'right', '연속 손실 최대 벌점', '', 'float', _getr('burstMax'), _set('burstMax', float)),
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
    ('flowZeroRandomTrain', '학습 실행', 'right', '학습 때 흐름 0도 무작위', '검증, 평가는 항상 고정', 'bool', _getr('flowZeroRandomTrain'),
     _set('flowZeroRandomTrain', bool)),
    ('trainSeedStart', '학습 실행', 'right', '학습 시드 시작', '', 'int', _getr('trainSeedStart'), _set('trainSeedStart', int)),
    ('saveEvery', '학습 실행', 'right', '중간 저장 주기', '에피소드', 'int', _getr('saveEvery'), _set('saveEvery', int)),
    ('torchSeed', '학습 실행', 'right', '신경망 시드', '', 'int', _getr('torchSeed'), _set('torchSeed', int)),
    ('evalEvery', '검증 평가 (학습 중)', 'right', '검증 주기 (0이면 안 함)', '에피소드마다', 'int', _getr('evalEvery'), _set('evalEvery', int)),
    ('valSeeds', '검증 평가 (학습 중)', 'right', '검증 시드', 'ε 0, 학습 없음', 'fixed', lambda P, RL: f'{RL.valSeeds[0]} ~ {RL.valSeeds[-1]}', None),
]
P_KEYS = {f[0] for f in FIELDS if f[2] == 'left'}


def build_config(overrides=None):
    # 기본 설정 + 화면에서 바꾼 값 -> (P, RL)
    # 순서: P 덮어쓰기 -> config_rl(P) (기한, 흐름 수 등 P에서 따라오는 값 반영) -> RL 덮어쓰기
    overrides = overrides or {}
    P = config_isl()
    P.nodeLogEnable = False
    P.bgMode = 'event'
    for key, _, side, _, _, kind, _, setter in FIELDS:
        if side == 'left' and setter and key in overrides:
            setter(P, overrides[key])
    RL = config_rl(P)
    for key, _, side, _, _, kind, _, setter in FIELDS:
        if side == 'right' and setter and key in overrides:
            setter(RL, overrides[key])
    return P, RL


def describe(overrides=None):
    # 화면에 보낼 칸 목록: 기본값(default)과 지금 값(value)을 같이
    P0, RL0 = build_config({})
    P, RL = build_config(overrides)
    out = []
    for key, group, side, label, unit, kind, getter, _ in FIELDS:
        item = dict(key=key, group=group, side=side, label=label, unit=unit, kind=kind,
                    default=getter(P0, RL0), value=getter(P, RL))
        if key == 'levelRatio':   # 단계별 지역 핫스팟 발생 간격, 지속 (ms = step)
            item['table'] = {k: v for k, v in EVENT_LEVELS.items()}
        out.append(item)
    return out
