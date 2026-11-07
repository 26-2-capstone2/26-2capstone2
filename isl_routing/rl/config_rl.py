# 강화학습 설정값 파일 - 관측, 보상, 신경망, 학습, 탐험에 쓰일 값 
# (시뮬레이터 값 : config_isl.py / 강화학습 값 : config_rl.py 에서 수정)
#
# 정규화 기준값 (큐 크기, 기한, TTL)은 시뮬레이터 값에서 가져옴 
# -> 시뮬레이터 설정값을 바꾸면 rl 설정값도 자동변경
# [시작값] 표시는 처음 돌려 보고 학습 곡선을 보며 조정할 값
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
    RL.maskMode = 'link'                   # 'link': 없는 방향만 막음 (꽉 찬 큐, 기한 초과는 손실 보상으로 직접 배움)
                                           # 'full': 예전 방식, 꽉 찬 큐와 기한 안에 못 가는 방향도 막음 (비교용)
    RL.normQueue = P.queueMax              # 큐 길이, 이웃 부하 N ÷ 200
    RL.deltaWindow = 10                    # 큐 증가 속도: 현재 - 10 step 전 큐 길이
    RL.normDelta = 10 * P.linkCapacity     # 큐 증가 속도 ÷ 50 (10 step 동안 비울 수 있는 최대 개수), -1~1로 자름
    RL.overflowWindow = 300                # 최근 큐 넘침: min(지난 시간, 300) ÷ 300 (핫스팟 켜짐 평균 150~450의 가운데)
    RL.normDist = max(P.numPlanes // 2 if getattr(P, 'wrapP', False) else P.numPlanes - 1,
                      P.satsPerPlane // 2 if getattr(P, 'wrapS', False) else P.satsPerPlane - 1)   # 남은 거리 ÷ 한 축 최대 거리 (6x6: 5, 원형이면 절반)
    RL.normDeadline = P.deadline           # 남은 기한 ÷ 70
    RL.normTtl = P.ttlInit                 # 남은 TTL ÷ 20

    # ---- 보상 (rl_reward.py) ----
    RL.rewardHopScale = P.deadline         # 홉 보상 = -(링크 지연 + 큐 길이 ÷ 링크 용량) ÷ 70
    RL.rewardHopQueue = False              # 홉 보상 = -링크 지연 ÷ 70 (큐 항목 없음, 7차 기준). True면 이전처럼 큐 항목 포함
    RL.rewardOnTime = 0.5                  # 기한 내 도착 (끝)
    RL.rewardSingleLoss = -0.1            # 단발 손실 (1~2개): 오버플로, 기한 초과, TTL 만료 (끝)
    RL.burstEnabled = True                 # False면 연속 손실도 단발 손실과 같은 보상 (대조 실험)
    RL.burstBase = 0.2                     # 연속 손실 (3개 이상) k번째 패킷: -min(1.0, 0.2 + 0.1 x max(0, k - 3))
    RL.burstStep = 0.1                     #   구간 전체(처음 2개 포함)에 단발 손실 대신 적용
    RL.burstMax = 1.0

    # ---- 신경망 (rl_agent.py) ----
    RL.hidden = [64, 64]                   # 중간층 크기: 입력 24 -> 64 -> 64 -> 출력 4 (방향별 Q값)
    RL.lr = 1e-4                           # 학습률 (Adam), SB3 DQN 기본값 (기존 1e-3)        [학습 안정화 계획]
    RL.gamma = 0.95                        # 할인율 γ [시작값]
    RL.doubleDQN = True                    # Double DQN

    # ---- 리플레이 버퍼, 학습 ----
    RL.bufferSize = 1000000                # 리플레이 버퍼 크기 (경험 수), SB3 기본값 (기존 20만)  [학습 안정화 계획]
    RL.batchSize = 64                      # 한 번 학습에 꺼내는 경험 수                         [시작값]
    RL.learnStart = 50000 * P.numFlows     # 버퍼에 이만큼 쌓인 뒤부터 학습 시작 (흐름 하나당 5만 = 에피소드 약 6)
    RL.trainEvery = 4 * P.numFlows         # 결정 몇 번마다 한 번 학습 (흐름 수에 비례 -> 에피소드당 학습 횟수는 흐름 1개 때와 같음)
    RL.targetUpdate = 2500                 # 학습 몇 번마다 타깃 신경망을 통째로 복사 (hard update, 에피소드 약 1.1개마다)
    RL.gradClip = 10.0                     # 기울기 최대 크기
    RL.tau = 0.0                           # 0: hard update (7차 기준). 0보다 크면 매 학습마다 τ만큼 섞음 (soft update, 6차 0.005: 학습이 빨리 시작됨)

    # ---- 탐험 (ε-greedy, 온라인 학습) ----
    RL.epsStart = 1.0                      # 처음엔 전부 무작위
    RL.epsEnd = 0.05                       # 마지막엔 5%만 무작위
    RL.epsDecaySteps = 100000 * P.numFlows   # 이 결정 수에 걸쳐 1.0 -> 0.05로 줄임 (흐름 하나당 10만 = 에피소드 약 13)

    # ---- 학습 실행 (train_rl.py) ----
    RL.trainLevels = ['high', 'severe']    # 학습에 쓰는 혼잡 단계
    RL.flowZeroRandomTrain = True          # 학습 에피소드마다 흐름 0의 출발, 도착도 무작위 (검증, 평가는 항상 (0,0) -> (5,5))
    RL.trainLevelMode = 'weighted'         # 'weighted': 아래 비율로 에피소드마다 무작위로 고름, 'cycle': base, high, severe 차례로 돌아가며 (이전 방식)
    RL.trainLevelWeights = {'high': 1, 'severe': 2}   # severe 강조 혼합, 순서는 trainSeedStart로 고정
    RL.trainSeedStart = 1001               # 학습용 시드 시작 (평가용 시드 1~20은 학습에 절대 안 씀)
    RL.trainEpisodes = 80                  # 학습 에피소드 수 (10초짜리)
    RL.evalSeeds = list(range(1, 21))      # 평가용 시드 1~20 (A, B와 같은 조건)
    RL.torchSeed = 0                       # 신경망 초기값, 버퍼 샘플링 난수 시드

    # ---- 저장 ----
    RL.modelDir = 'rl_models'              # 학습된 신경망 저장 폴더
    RL.saveEvery = 10                      # 에피소드 몇 개마다 체크포인트 저장

    # ---- 학습 중 검증 평가 (학습 곡선용, train_rl.py) ----
    RL.evalEvery = 5                       # 에피소드 몇 개마다 학습을 멈추고 검증 평가 (학습 시작 전에도 1번)
    RL.valSeeds = list(range(501, 504))    # 검증용 시드 501~503 (학습 1001~, 최종 평가 1~20과 겹치지 않게)
    RL.valLevels = ['high', 'severe']      # 검증할 혼잡 단계 (ε 0, 학습 없음)

    return RL
