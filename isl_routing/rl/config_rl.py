# 강화학습 설정값 파일 - 관측, 보상, 신경망, 학습, 탐험에 쓰일 값 
# (시뮬레이터 값 : config_isl.py / 강화학습 값 : config_rl.py 에서 수정)
#
# 정규화 기준값 (큐 크기, 기한, TTL)은 시뮬레이터 값에서 가져옴 
# -> 시뮬레이터 설정값을 바꾸면 rl 설정값도 자동변경
# [시작값] 표시는 처음 돌려 보고 학습 곡선을 보며 조정할 값
import os
from types import SimpleNamespace


def config_rl(P):
    # 입력: P (config_isl()의 시뮬레이터 설정)
    # 출력: RL (강화학습 설정)
    RL = SimpleNamespace()

    # ---- 관측 벡터 (rl_state.py) ----
    RL.stateMode = 'coarse'                # 15개 (7차 기준): 큐 3단계 4 + 30 step 전 이웃 부하 4 + 링크 유무 4 + 남은 거리 2 + 남은 기한 1
                                           # 그 밖의 값 (이전 실험용, 코드로만 바꿈): 'full' 24개, 'noTrend' 16개
    RL.obsDim = {'full': 24, 'noTrend': 16, 'coarse': 15}[RL.stateMode]
    RL.qLevelLow = 0.5 * P.queueMax        # coarse 큐 3단계: 100개 미만 여유 0, 100~150개 보통 0.5, 150개 이상 혼잡 1
    RL.qLevelHigh = 0.75 * P.queueMax
    RL.nbrDelay = 30                       # coarse 이웃 부하: 30 step 전 값
                                           # full 24개: 큐 4 + 이웃 부하 4 + 큐 증가 속도 4 + 최근 큐 넘침 4 + 링크 유무 4 + 남은 거리 2 + 남은 기한 1 + 남은 TTL 1
    RL.numActions = 4                      # 행동 4개 : 상, 하, 좌, 우
    RL.maskMode = os.environ.get('RL_MASK_MODE', 'noBack')   # 'noBack': 없는 방향 + 방금 온 위성 쪽을 막음 (두 위성 사이 왕복 차단, 11/27)
                                           # 환경 변수 RL_MASK_MODE로 바꿈 (모델에 마스크가 저장되지 않아 학습, 적응, 평가 모두 같은 값으로 실행해야 함)
                                           # 'link': 없는 방향만 막음 (11/26 6x11 모델까지)
                                           # 'full': 예전 방식, 꽉 찬 큐와 기한 안에 못 가는 방향도 막음 (비교용)
    RL.normQueue = P.queueMax              # 큐 길이, 이웃 부하 N ÷ 200
    RL.deltaWindow = 10                    # 큐 증가 속도: 현재 - 10 step 전 큐 길이
    RL.normDelta = 10 * P.linkCapacity     # 큐 증가 속도 ÷ 50 (10 step 동안 비울 수 있는 최대 개수), -1~1로 자름
    RL.overflowWindow = 300                # 최근 큐 넘침: min(지난 시간, 300) ÷ 300 (핫스팟 켜짐 평균 150~450의 가운데)
    RL.distMode = 'log'                    # 남은 거리 표현 (rl_state.dist_feature). 'log': 로그 눈금 (11/27), 'clip': ÷ normDist 후 자름 (11/23)
    RL.distLogMax = 64                     # 'log': 64칸에서 1. 망 크기와 상관없이 같은 값이어야 다른 격자로 옮긴 모델이 같은 뜻으로 읽음 (72x22는 65칸 이상만 1로 잘림)
    RL.normDist = 5                        # 'clip': 남은 거리 ÷ 5칸, -1~1로 자름 (5칸 이상은 모두 1이라 6x11 세로 10칸에서 왕복 문제)
    RL.normDeadline = P.deadline           # 남은 기한 ÷ 측정 흐름 기한 (6x6: 70)
    RL.normTtl = P.ttlInit                 # 남은 TTL ÷ 20

    # ---- 보상 (rl_reward.py) ----
    RL.rewardHopScale = P.deadline         # 홉 보상 = -(링크 지연 + 큐 길이 ÷ 링크 용량) ÷ 측정 흐름 기한 (6x6: 70)
    RL.rewardHopQueue = False              # 홉 보상 = -링크 지연 ÷ 기한 (큐 항목 없음, 7차 기준). True면 이전처럼 큐 항목 포함
    RL.rewardOnTime = 0.5                  # 기한 내 도착 (끝)
    RL.rewardSingleLoss = -0.1            # 단발 손실 (1~2개): 오버플로, 기한 초과, TTL 만료 (끝)
    RL.burstEnabled = True                 # False면 연속 손실도 단발 손실과 같은 보상 (대조 실험)
    RL.burstBase = 0.2                     # 연속 손실 (3개 이상) k번째 패킷: -min(1.0, 0.2 + 0.1 x max(0, k - 3))
    RL.burstStep = 0.1                     #   구간 전체(처음 2개 포함)에 단발 손실 대신 적용
    RL.burstMax = 1.0
                                           # 11/26: 보상은 11/7(7차) 그대로. 이리듐 때 넣은 위험 링크 벌점, 연속 손실 시작 벌점, 패킷당 고정 벌점은 뺌

    # ---- 신경망 (rl_agent.py) ----
    RL.hidden = [64, 64]                   # 중간층 크기: 입력 15 -> 64 -> 64 -> 출력 4 (방향별 Q값)
    RL.lr = 1e-4                           # 학습률 (Adam), SB3 DQN 기본값 (기존 1e-3)        [학습 안정화 계획]
    # 망 크기 비례 기준: 측정 흐름 최소 홉 ÷ 15 (6x11 측정 흐름, 11/27 학습 성공 설정 = 1배). 36x36: 70홉 -> 4.67배
    RL.refHops = 15
    hopScale = P.maxFlowHops / RL.refHops
    RL.gamma = 0.95 ** (1 / hopScale)      # 할인율 γ: 출발점에서 보이는 도착 보상 0.95^15 = 0.46이 망 크기와 상관없이 같게 (6x11 0.95, 36x36 0.989)
    RL.doubleDQN = True                    # Double DQN

    # ---- 리플레이 버퍼, 학습 ----
    RL.bufferSize = 1000000                # 리플레이 버퍼 크기 (경험 수), SB3 기본값 (기존 20만)  [학습 안정화 계획]
    RL.batchSize = 64                      # 한 번 학습에 꺼내는 경험 수                         [시작값]
    # 아래 결정 수, 학습 횟수 기준값은 망 크기(hopScale)에도 비례: 큰 망은 패킷당 결정이 많아 에피소드당 결정도 많음 -> 에피소드 단위 일정이 같게
    RL.learnStart = round(50000 * P.numFlows * hopScale)   # 버퍼에 이만큼 쌓인 뒤부터 학습 시작 (6x11: 20만 = 에피소드 약 5)
    RL.trainEvery = 4 * P.numFlows         # 결정 몇 번마다 한 번 학습 (흐름 수에 비례 -> 에피소드당 학습 횟수는 흐름 1개 때와 같음)
    RL.targetUpdate = round(2500 * hopScale)   # 학습 몇 번마다 타깃 신경망을 통째로 복사 (hard update, 6x11 2500 = 에피소드 약 1개마다)
    RL.gradClip = 10.0                     # 기울기 최대 크기
    RL.tau = 0.0                           # 0: hard update (7차 기준). 0보다 크면 매 학습마다 τ만큼 섞음 (soft update, 6차 0.005: 학습이 빨리 시작됨)

    # ---- 탐험 (ε-greedy, 온라인 학습) ----
    RL.epsStart = 1.0                      # 처음엔 전부 무작위
    RL.epsEnd = 0.05                       # 마지막엔 5%만 무작위
    RL.epsDecaySteps = round(100000 * P.numFlows * hopScale)   # 이 결정 수에 걸쳐 1.0 -> 0.05로 줄임 (6x11: 40만 = 에피소드 약 10)

    # ---- 학습 실행 (train_rl.py) ----
    RL.trainLevels = ['high', 'severe']    # 학습에 쓰는 혼잡 단계
    RL.flowZeroRandomTrain = 'any'         # 학습, 적응 때 측정 흐름: 모든 쌍 중 무작위 (많은 경로를 배움, 11/27). 검증, 평가는 P.flowZeroTest ('far')
    RL.trainLevelMode = 'weighted'         # 'weighted': 아래 비율로 에피소드마다 무작위로 고름, 'cycle': base, high, severe 차례로 돌아가며 (이전 방식)
    RL.trainLevelWeights = {'high': 1, 'severe': 2}   # severe 강조 혼합, 순서는 trainSeedStart로 고정
    RL.trainSeedStart = 1001               # 학습용 시드 시작 (평가용 시드 1~20은 학습에 절대 안 씀)
    RL.trainEpisodes = 100                 # 학습 에피소드 수 (10초짜리, 11/27 80 -> 100: 학습 쌍이 다양해져 더 길게)
    RL.evalSeeds = list(range(1, 21))      # 평가용 시드 1~20 (A, B와 같은 조건)
    RL.torchSeed = 0                       # 신경망 초기값, 버퍼 샘플링 난수 시드

    # ---- 적응 (rl/adapt_rl.py): 다른 격자로 학습한 모델을 새 격자에서 짧게 추가 학습 (학습 -> 적응 -> 평가) ----
    RL.trainGrid = 'grid:10x10'            # run.py "C 학습"의 기본 학습 격자 (학습 전용, 평가는 다른 격자로)
    RL.adaptEpisodes = 5                   # 적응 에피소드 수 (10초짜리)
    RL.adaptSeedStart = 2001               # 적응 전용 시드 (학습 1001~, 검증 501~503, 최종 평가 1~20과 겹치지 않음)
    RL.adaptEps = 0.05                     # 적응 중 ε (처음부터 끝까지 고정, 학습 끝의 값과 같음)
    RL.adaptLr = 1e-5                      # 적응 학습률 (학습 1e-4의 1/10, 배운 것을 크게 흔들지 않게)
    RL.adaptLearnStart = 10000 * P.numFlows   # 적응: 버퍼가 비어서 시작 -> 이만큼 쌓이면 학습 시작 (에피소드 1개 안쪽)
                                              #   망 크기에 비례시키지 않음: 적응 초반엔 패킷이 일찍 버려져 결정 수가 홉 수만큼 늘지 않음 (36x36 적응 1번째 약 7.5만)

    # ---- 저장 ----
    RL.modelDir = 'rl_models'              # 학습된 신경망 저장 폴더
    RL.saveEvery = 10                      # 에피소드 몇 개마다 체크포인트 저장

    # ---- 학습 중 검증 평가 (학습 곡선용, train_rl.py) ----
    RL.evalEvery = 5                       # 에피소드 몇 개마다 학습을 멈추고 검증 평가 (학습 시작 전에도 1번)
    RL.valSeeds = list(range(501, 504))    # 검증용 시드 501~503 (학습 1001~, 최종 평가 1~20과 겹치지 않게)
    RL.valLevels = ['high', 'severe']      # 검증할 혼잡 단계 (ε 0, 학습 없음)

    return RL


# 혼잡 단계 비율 -> 에피소드별 단계 (train_rl.py가 씀)
# PyTorch 없이 불러올 수 있게 이 파일에 둠
def apply_level_ratio(RL, ratio):
    # 'b:h:s' (예 '1:1:2') -> 학습 단계 비율. 0인 단계는 학습과 검증에서 뺌
    w = [float(x) for x in str(ratio).split(':')]
    if len(w) != 3 or min(w) < 0 or sum(w) <= 0:
        raise ValueError(f'혼잡 단계 비율은 base:high:severe 형식 (예 0:1:2): {ratio}')
    levels = [lv for lv, x in zip(['base', 'high', 'severe'], w) if x > 0]
    RL.trainLevelMode = 'weighted'
    RL.trainLevels = levels
    RL.trainLevelWeights = {lv: x for lv, x in zip(['base', 'high', 'severe'], w) if x > 0}
    RL.valLevels = list(levels)
    return RL


def train_level_sequence(RL, numEpisodes, seedStart=None):
    # 에피소드별 혼잡 단계 목록. weighted는 비율대로 무작위 (seedStart, 기본 trainSeedStart로 고정해서 학습 시드가 달라도 같은 순서)
    import numpy as np
    if getattr(RL, 'trainLevelMode', 'cycle') != 'weighted':
        return [RL.trainLevels[ep % len(RL.trainLevels)] for ep in range(numEpisodes)]
    w = np.array([RL.trainLevelWeights[lv] for lv in RL.trainLevels], dtype=float)
    rng = np.random.RandomState(RL.trainSeedStart if seedStart is None else seedStart)
    return [str(lv) for lv in rng.choice(RL.trainLevels, size=numEpisodes, p=w / w.sum())]
