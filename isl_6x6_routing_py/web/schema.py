# 변수 설정 화면의 칸 목록 - 화면 칸 하나 = 코드 변수 하나 (config_isl.py, config_rl.py)
#
# 기본값은 항상 config_isl(), config_rl()에서 읽고, 화면에서 바꾼 값(overrides)만 그 위에 덮어씀
# -> 설정 파일의 확정값 자체는 바꾸지 않음
#
# kind: int, float, pair(칸 2개), choice(하나 고르기), multi(여러 개 고르기), bool, fixed(바꿀 수 없음)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_6x6_routing_py

from config_isl import BG_LEVELS, apply_bg_level, config_isl
from rl.config_rl import config_rl

LEVELS = list(BG_LEVELS)


def _set_delay(P, v):
    ud, lr = v
    P.linkDelay[:] = [ud, ud, lr, lr]


# (key, 묶음, 왼쪽/오른쪽, 이름, 단위, 종류, 읽기, 쓰기)
FIELDS = [
    # ---- 왼쪽: 시뮬레이터 (config_isl.py) ----
    ('numPlanes', '네트워크', 'left', '궤도면 수 (좌우)', '개', 'int', lambda P, RL: P.numPlanes, lambda P, v: setattr(P, 'numPlanes', int(v))),
    ('satsPerPlane', '네트워크', 'left', '궤도면당 위성 수 (상하)', '개', 'int', lambda P, RL: P.satsPerPlane, lambda P, v: setattr(P, 'satsPerPlane', int(v))),
    ('srcSat', '네트워크', 'left', '출발 위성 (p, s)', '', 'pair', lambda P, RL: [int(x) for x in P.srcSat], lambda P, v: P.srcSat.__setitem__(slice(None), [int(x) for x in v])),
    ('dstSat', '네트워크', 'left', '목적지 위성 (p, s)', '', 'pair', lambda P, RL: [int(x) for x in P.dstSat], lambda P, v: P.dstSat.__setitem__(slice(None), [int(x) for x in v])),
    ('queueMax', '네트워크', 'left', '링크 큐 크기', '개', 'int', lambda P, RL: P.queueMax, lambda P, v: setattr(P, 'queueMax', int(v))),
    ('linkCapacity', '네트워크', 'left', '링크 전송량', '개 / ms', 'int', lambda P, RL: P.linkCapacity, lambda P, v: setattr(P, 'linkCapacity', int(v))),
    ('linkDelay', '네트워크', 'left', '링크 지연 (상하, 좌우)', 'ms', 'pair', lambda P, RL: [int(P.linkDelay[0]), int(P.linkDelay[2])], lambda P, v: _set_delay(P, [int(x) for x in v])),
    ('processingDelay', '네트워크', 'left', '처리 지연', 'ms', 'int', lambda P, RL: P.processingDelay, lambda P, v: setattr(P, 'processingDelay', int(v))),
    ('deadline', '패킷', 'left', '기한', 'ms', 'int', lambda P, RL: P.deadline, lambda P, v: setattr(P, 'deadline', int(v))),
    ('ttlInit', '패킷', 'left', 'TTL', '홉', 'int', lambda P, RL: P.ttlInit, lambda P, v: setattr(P, 'ttlInit', int(v))),
    ('genRate', '패킷', 'left', '초당 패킷', '개', 'int', lambda P, RL: P.genRate, lambda P, v: setattr(P, 'genRate', int(v))),
    ('packetSize', '패킷', 'left', '패킷 크기', 'Byte', 'int', lambda P, RL: P.packetSize, lambda P, v: setattr(P, 'packetSize', int(v))),
    ('burstMinLen', '패킷', 'left', '연속 손실 기준', '개 이상', 'int', lambda P, RL: P.burstMinLen, lambda P, v: setattr(P, 'burstMinLen', int(v))),
    ('bgLevel', '배경 트래픽 (핫스팟)', 'left', '혼잡 단계', '', 'choice', lambda P, RL: P.bgLevel, lambda P, v: apply_bg_level(P, v)),
    ('bgLoad', '배경 트래픽 (핫스팟)', 'left', '핫스팟 세기', '배', 'pair', lambda P, RL: [P.bgLoadMin, P.bgLoadMax], lambda P, v: (setattr(P, 'bgLoadMin', float(v[0])), setattr(P, 'bgLoadMax', float(v[1])))),
    ('bgBlockLoad', '배경 트래픽 (핫스팟)', 'left', '막힘 기준 세기', '배', 'float', lambda P, RL: P.bgBlockLoad, lambda P, v: setattr(P, 'bgBlockLoad', float(v))),
    ('bgRelWeight', '배경 트래픽 (핫스팟)', 'left', '주 흐름 쪽 가중치', '', 'float', lambda P, RL: P.bgRelWeight, lambda P, v: setattr(P, 'bgRelWeight', float(v))),
    ('bgTtl', '배경 트래픽 (핫스팟)', 'left', '배경 패킷 TTL', '홉', 'int', lambda P, RL: P.bgTtl, lambda P, v: setattr(P, 'bgTtl', int(v))),
    ('simTime', '실험 (평가)', 'left', '에피소드 길이', '초', 'float', lambda P, RL: P.simTime / 1000, lambda P, v: setattr(P, 'simTime', int(float(v) * 1000))),
    ('maxDrainTime', '실험 (평가)', 'left', '남은 패킷 처리 시간', 'ms', 'int', lambda P, RL: P.maxDrainTime, lambda P, v: setattr(P, 'maxDrainTime', int(v))),
    ('numEpisodes', '실험 (평가)', 'left', '평가 에피소드 수', '개', 'int', lambda P, RL: P.numEpisodes, lambda P, v: setattr(P, 'numEpisodes', int(v))),
    ('evalSeeds', '실험 (평가)', 'left', '평가 시드', '학습에 쓰지 않음', 'fixed', lambda P, RL: '1 ~ 20', None),
    # ---- 오른쪽: 강화학습 (config_rl.py) ----
    ('obsDim', '에이전트 구조', 'right', '관측 숫자', '개', 'fixed', lambda P, RL: RL.obsDim, None),
    ('numActions', '에이전트 구조', 'right', '행동 (상, 하, 좌, 우)', '개', 'fixed', lambda P, RL: RL.numActions, None),
    ('hidden', '에이전트 구조', 'right', '신경망 중간층', '개', 'pair', lambda P, RL: list(RL.hidden), lambda RL, v: setattr(RL, 'hidden', [int(x) for x in v])),
    ('doubleDQN', '에이전트 구조', 'right', 'Double DQN', '', 'bool', lambda P, RL: RL.doubleDQN, lambda RL, v: setattr(RL, 'doubleDQN', bool(v))),
    ('rewardOnTime', '보상', 'right', '기한 내 도착', '', 'float', lambda P, RL: RL.rewardOnTime, lambda RL, v: setattr(RL, 'rewardOnTime', float(v))),
    ('rewardSingleLoss', '보상', 'right', '단발 손실', '', 'float', lambda P, RL: RL.rewardSingleLoss, lambda RL, v: setattr(RL, 'rewardSingleLoss', float(v))),
    ('burstBase', '보상', 'right', '연속 손실 기본 벌점', '', 'float', lambda P, RL: RL.burstBase, lambda RL, v: setattr(RL, 'burstBase', float(v))),
    ('burstStep', '보상', 'right', '연속 손실 증가폭', '개마다', 'float', lambda P, RL: RL.burstStep, lambda RL, v: setattr(RL, 'burstStep', float(v))),
    ('burstMax', '보상', 'right', '연속 손실 최대 벌점', '', 'float', lambda P, RL: RL.burstMax, lambda RL, v: setattr(RL, 'burstMax', float(v))),
    ('rewardHopScale', '보상', 'right', '홉 벌점 나눔값', '= 기한', 'fixed', lambda P, RL: RL.rewardHopScale, None),
    ('lr', 'DQN 학습', 'right', '학습률 (Adam)', '', 'float', lambda P, RL: RL.lr, lambda RL, v: setattr(RL, 'lr', float(v))),
    ('gamma', 'DQN 학습', 'right', '할인율 γ', '', 'float', lambda P, RL: RL.gamma, lambda RL, v: setattr(RL, 'gamma', float(v))),
    ('bufferSize', 'DQN 학습', 'right', '경험 버퍼 크기', '장', 'int', lambda P, RL: RL.bufferSize, lambda RL, v: setattr(RL, 'bufferSize', int(v))),
    ('batchSize', 'DQN 학습', 'right', '한 번에 꺼내는 수', '장', 'int', lambda P, RL: RL.batchSize, lambda RL, v: setattr(RL, 'batchSize', int(v))),
    ('learnStart', 'DQN 학습', 'right', '학습 시작', '장 이후', 'int', lambda P, RL: RL.learnStart, lambda RL, v: setattr(RL, 'learnStart', int(v))),
    ('trainEvery', 'DQN 학습', 'right', '학습 주기', '번 결정마다', 'int', lambda P, RL: RL.trainEvery, lambda RL, v: setattr(RL, 'trainEvery', int(v))),
    ('targetUpdate', 'DQN 학습', 'right', '타깃 신경망 갱신', '번 학습마다', 'int', lambda P, RL: RL.targetUpdate, lambda RL, v: setattr(RL, 'targetUpdate', int(v))),
    ('gradClip', 'DQN 학습', 'right', '기울기 최대 크기', '', 'float', lambda P, RL: RL.gradClip, lambda RL, v: setattr(RL, 'gradClip', float(v))),
    ('eps', '탐험 (ε-greedy)', 'right', 'ε 시작, 끝', '', 'pair', lambda P, RL: [RL.epsStart, RL.epsEnd], lambda RL, v: (setattr(RL, 'epsStart', float(v[0])), setattr(RL, 'epsEnd', float(v[1])))),
    ('epsDecaySteps', '탐험 (ε-greedy)', 'right', 'ε 줄이는 기간', '번 결정', 'int', lambda P, RL: RL.epsDecaySteps, lambda RL, v: setattr(RL, 'epsDecaySteps', int(v))),
    ('trainLevels', '학습 실행', 'right', '학습할 혼잡 단계', '', 'multi', lambda P, RL: list(RL.trainLevels), lambda RL, v: setattr(RL, 'trainLevels', [x for x in LEVELS if x in v] or list(LEVELS))),
    ('trainEpisodes', '학습 실행', 'right', '학습 에피소드 수', '개', 'int', lambda P, RL: RL.trainEpisodes, lambda RL, v: setattr(RL, 'trainEpisodes', int(v))),
    ('trainSeedStart', '학습 실행', 'right', '학습 시드 시작', '', 'int', lambda P, RL: RL.trainSeedStart, lambda RL, v: setattr(RL, 'trainSeedStart', int(v))),
    ('saveEvery', '학습 실행', 'right', '중간 저장 주기', '에피소드', 'int', lambda P, RL: RL.saveEvery, lambda RL, v: setattr(RL, 'saveEvery', int(v))),
    ('torchSeed', '학습 실행', 'right', '신경망 시드', '', 'int', lambda P, RL: RL.torchSeed, lambda RL, v: setattr(RL, 'torchSeed', int(v))),
]
P_KEYS = {f[0] for f in FIELDS if f[2] == 'left'}


def build_config(overrides=None):
    # 기본 설정 + 화면에서 바꾼 값 -> (P, RL)
    # 순서: P 덮어쓰기 -> config_rl(P) (기한 등 P에서 따라오는 값 반영) -> RL 덮어쓰기
    overrides = overrides or {}
    P = config_isl()
    P.nodeLogEnable = False
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
        if key == 'bgLevel':
            item['options'] = LEVELS
            item['table'] = {k: v for k, v in BG_LEVELS.items()}
        if key == 'trainLevels':
            item['options'] = LEVELS
        out.append(item)
    return out
