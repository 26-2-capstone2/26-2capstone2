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
    RL.obsDim = 20  # 관측 벡터 수 20개  (큐 길이 4 + 위성부하 4 + 링크점유율 4 + 링크유무 4 + 목적지남은거리 2 + 남은 기한 1 + 남은 TTL 1)                     
    RL.numActions = 4                      # 행동 4개 : 상, 하, 좌, 우 (없는 방향, 꽉 찬 큐는 마스크로 막음)
    RL.normQueue = P.queueMax              # 큐 길이, 이웃 부하 N ÷ 200
    RL.normDist = max(P.numPlanes, P.satsPerPlane) - 1   # 남은 거리 ÷ 5 (6x6 격자에서 한 축 최대 거리)
    RL.normDeadline = P.deadline           # 남은 기한 ÷ 70
    RL.normTtl = P.ttlInit                 # 남은 TTL ÷ 20

    # ---- 보상 (rl_reward.py) ----
    RL.rewardHopScale = P.deadline         # 홉 보상 = -(링크 지연 + 큐 길이 ÷ 링크 용량) ÷ 70
    RL.rewardOnTime = 1.0                  # 기한 내 도착 (끝)
    RL.rewardLoss = -1.0                   # 손실: 오버플로, 기한 초과, TTL 만료 (끝)
    RL.consecPenalty = 0.0                 # 연속 손실 추가 벌점 (팀원의 패킷 번호, 연속 손실 정의가 나오면 켬)

    # ---- 신경망 (rl_agent.py) ----
    RL.hidden = [64, 64]                   # 중간층 크기: 입력 20 -> 64 -> 64 -> 출력 4 (방향별 Q값)
    RL.lr = 1e-3                           # 학습률 (Adam)                                   [시작값]
    RL.gamma = 0.95                        # 할인율 γ (한 패킷이 약 10~20홉이라 너무 작으면 근시안적)  [시작값]
    RL.doubleDQN = True                    # Double DQN (Q값 과대평가 완화)

    # ---- 리플레이 버퍼, 학습 ----
    RL.bufferSize = 200000                 # 리플레이 버퍼 크기 (경험 수)                       [시작값]
    RL.batchSize = 64                      # 한 번 학습에 꺼내는 경험 수                         [시작값]
    RL.learnStart = 5000                   # 버퍼에 이만큼 쌓인 뒤부터 학습 시작                   [시작값]
    RL.trainEvery = 4                      # 결정 몇 번마다 한 번 학습                            [시작값]
    RL.targetUpdate = 2000                 # 학습 몇 번마다 타깃 신경망을 복사                     [시작값]
    RL.gradClip = 10.0                     # 기울기 최대 크기 (학습 폭주 방지)

    # ---- 탐험 (ε-greedy, 온라인 학습) ----
    RL.epsStart = 1.0                      # 처음엔 전부 무작위
    RL.epsEnd = 0.05                       # 마지막엔 5%만 무작위
    RL.epsDecaySteps = 300000              # 이 결정 수에 걸쳐 1.0 -> 0.05로 줄임 (직선)          [시작값]

    # ---- 학습 실행 (train_rl.py) ----
    RL.trainLevels = ['base', 'high', 'severe']   # 혼잡 세 단계를 섞어서 학습 (에피소드마다 돌아가며)
    RL.trainSeedStart = 1001               # 학습용 시드 시작 (평가용 시드 1~20은 학습에 절대 안 씀)
    RL.trainEpisodes = 60                  # 학습 에피소드 수 (30초짜리, 단계마다 20개)           [시작값]
    RL.evalSeeds = list(range(1, 21))      # 평가용 시드 1~20 (A, B, D와 같은 조건)
    RL.torchSeed = 0                       # 신경망 초기값, 버퍼 샘플링 난수 시드

    # ---- 저장 ----
    RL.modelDir = 'rl_models'              # 학습된 신경망 저장 폴더 (홈 폴더 아래)
    RL.saveEvery = 10                      # 에피소드 몇 개마다 체크포인트 저장

    return RL
