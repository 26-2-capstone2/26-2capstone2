# 설정값 모음 - 시뮬레이션에 쓰이는 모든 변수값을 여기서 정함
# (값 바꾸려면 여기서 수정하면 됩니다!)
#
from types import SimpleNamespace

import numpy as np

# 혼잡 단계별 배경 트래픽 값 (P.bgLevel로 고름): 핫스팟 개수 범위, ON/OFF 평균 길이 (step)
# 나머지 배경 값(세기 0.7~2.0배, 막힘 기준 1.8, 주 흐름 쪽 가중치 3 등)은 모든 단계에서 같음
# 켜짐 + 꺼짐 = 900 step으로 맞춰 주기는 같고 켜진 시간 비율만 커짐
BG_LEVELS = {
    'base':   dict(bgNumMin=2, bgNumMax=5, bgOnMean=150, bgOffMean=750),   # 기본, 켜진 시간 약 1/6 (평상시)
    'high':   dict(bgNumMin=3, bgNumMax=6, bgOnMean=300, bgOffMean=600),   # 높음, 약 1/3 (붐비는 시간대)
    'severe': dict(bgNumMin=4, bgNumMax=7, bgOnMean=450, bgOffMean=450),   # 매우 높음, 약 1/2 (피크, 이벤트 상황)
}


def apply_bg_level(P, level):
    # 혼잡 단계 이름으로 위 표의 값을 P에 덮어씀 (config_isl 끝과 main_isl 실행 인자에서 사용)
    if level not in BG_LEVELS:
        raise ValueError(f'혼잡 단계는 {list(BG_LEVELS)} 중 하나: {level}')
    P.bgLevel = level
    for k, v in BG_LEVELS[level].items():
        setattr(P, k, v)
    return P


def config_isl():
    # ISL 2D Grid 라우팅 시뮬레이션 설정값
    P = SimpleNamespace()

    # ---- 네트워크 구조 ----
    P.numPlanes = 6                        # 궤도면 수 (좌/우)
    P.satsPerPlane = 6                     # 궤도면당 위성 수 (상/하)
    P.srcSat = np.array([0, 0])            # 출발 위성 (p,s)
    P.dstSat = np.array([5, 5])            # 도착 위성 (p,s)
    P.queueMax = 200                       # 링크별 큐 최대 용량 (packets)
    P.linkCapacity = 5                    # ISL 대역폭 (packets/step)
    P.linkDelay = np.array([7, 7, 2, 2])   # 링크 지연 [상 하 좌 우] (step)
    P.processingDelay = 0                  # 처리 지연 (step)

    # ---- 패킷 ----
    P.ttlInit = 20                         # TTL 초기값 (잔여 홉)
    P.deadline = 70                       # 기한 (step), 최소 경로 45 step + 여유 25 step (90에서 줄임: D_LA_Dijkstra도 기한 초과 손실이 나도록)
    P.burstMinLen = 3                      # 생성 순서상 실패가 3개 이상 이어지면 연속 손실 사건
    P.packetSize = 160                     # 패킷 크기 (Byte)

    # ---- 라우팅 알고리즘 ----
    P.routeName = 'B_LinkLoad'                 # 'A_Dijkstra': 최단 경로 (부하 무시), 'B_LinkLoad': 연속 손실 회피 + 링크 부하, 'D_LA_Dijkstra': 부하 고려 최단 경로

    # ---- B 라우팅 (연속 손실 회피 + 링크 부하) ----
    P.X = 0.5                              # Idle / Relatively Busy 경계
    P.Y = 0.8                              # Relatively Busy / Busy 경계
    P.k = 0.5                              # 가중치 (1: V만, 0: N만)
    P.holdTime = 300                       # 손실 직후 회피: 오버플로가 난 링크를 이 시간(step) 동안 피함 (핫스팟 켜짐 평균 150~450의 가운데)
    P.bAlternate = False                   # 연이은 패킷 나누기: True면 같은 위성에서 직전과 다른 방향으로 번갈아 보냄 (지금은 끔)
    P.riskRatio = 0.8                      # 넘칠 위험 회피: 큐가 이 비율 이상 찬 링크를 피함 (Busy 기준 Y와 같은 값)

    # ---- 실험 ----
    P.genRate = 60                         # 1초마다 생성하는 패킷 수 (일정 간격)
    P.epsilonList = [0, 0.1]               # 무작위 선택 확률 (0: 성능 측정용, 0.1: 데이터 수집용)
    P.simTime = 30000                      # 에피소드 1개의 길이 (step = 30초). 에피소드마다 큐가 비어 있는 상태로 시작
    P.numEpisodes = 20                     # 에피소드 개수 (총 시뮬레이션 = simTime x numEpisodes = 10분)
    P.maxDrainTime = 500                   # 생성 종료 후 남은 패킷 처리 최대 step [설정]
    P.randomSeed = 1                       # 난수 시드                             [설정]
    P.stepTime = 1e-3                      # 1 step = 1 ms (초 단위)

    # ---- 노드 기록 (node_log CSV: 노드 기준 상태) ----
    P.nodeLogEnable = True                 # False면 node_log 저장 안 함
    P.nodeLogInterval = 100                # 몇 step마다 노드 36개를 1줄씩 기록 (작을수록 파일이 커짐) [설정]

    # ---- 애니메이션 ----
    P.animDuration = 200                   # 애니메이션에 담을 step 수             [설정]
    P.animFrameInterval = 2                # 몇 step마다 한 프레임                 [설정]

    # ---- 배경 트래픽 (송신 큐 핫스팟) ----
    # 핫스팟 = 위성 하나의 한 방향 송신 큐가 과부하. 켜지면 큐가 차서 패킷이 버려지고, 꺼지면 서서히 비워짐
    # 핫스팟의 위치/개수/세기는 에피소드마다 시드로 무작위 선택 (bg_traffic.sample_hotspots). 같은 시드면 같은 시나리오
    # 에피소드 안에서는 핫스팟 위치가 고정, ON/OFF 시점만 계속 바뀜
    P.bgEnable = True                      # 배경 트래픽 On/Off
    P.bgScenarioSeed = 1                   # 첫 에피소드의 시나리오 시드. 에피소드 e는 시드+e를 씀 (None이면 실행마다 무작위 시작 시드)
                                           # 실행할 때 python main_isl.py 7 처럼 시작 시드를 직접 줄 수도 있음
    P.bgNumMin, P.bgNumMax = 2, 5          # 핫스팟(과부하 송신 큐) 개수 범위
    P.bgLoadMin, P.bgLoadMax = 0.7, 2.0    # 핫스팟별 세기 = 부하 x 링크 용량 (1.8 이상이면 큐가 금방 가득 참)
    P.bgBlockLoad = 1.8                    # 이 부하 이상이면 큐를 가득 채워 막는 것으로 간주 (우회 가능 여부 확인에 사용)
    P.bgRelWeight = 3.0                    # 주 흐름과 관련 있는 큐(목적지 쪽 방향)를 뽑을 가중치 (1.0이면 완전 균등)
    P.bgMinRelevant = 1                    # 관련 있는 큐가 최소 몇 개는 포함돼야 하는지
    P.bgOnMean = 150                       # ON 평균 길이 (step)
    P.bgOffMean = 750                      # OFF 평균 길이 (step)
    P.bgTtl = 20                           # 배경 패킷 TTL
    P.bgPoolSize = 20000                   # 동시에 존재할 수 있는 배경 패킷 수 (srcDrop > 0이면 키울 것)
    P.bgFlows = []                         # 아래 3개는 sample_hotspots가 채움
    P.bgOnRate = []
    P.bgSeed = 0
    P.bgLevel = 'base'                     # 혼잡 단계: 'base', 'high', 'severe' (위 BG_LEVELS 값으로 핫스팟 개수, ON/OFF를 덮어씀)
    apply_bg_level(P, P.bgLevel)

    return P
