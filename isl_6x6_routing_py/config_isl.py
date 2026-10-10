# 설정값 모음 - 시뮬레이션에 쓰이는 모든 변수값을 여기서 정함
# (값 바꾸려면 여기서 수정하면 됩니다!)
#
from types import SimpleNamespace

import numpy as np


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
    P.deadline = 70                       # 기한 (step)
    P.packetSize = 160                     # 패킷 크기 (Byte)

    # ---- 라우팅 알고리즘 ----
    P.routeName = 'routeB'                 # 'routeA': 최단 경로 (부하 무시), 'routeB': 부하 고려 (Liu 단순화)

    # ---- B 라우팅 (Liu et al. 단순화) ----
    P.X = 0.5                              # Idle / Relatively Busy 경계
    P.Y = 0.8                              # Relatively Busy / Busy 경계
    P.k = 0.5                              # 가중치 (1: V만, 0: N만)

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
    # 핫스팟 = 위성 하나의 한 방향 송신 큐가 과부하. 켜지면(ON) 큐가 차서 패킷이 버려지고, 꺼지면(OFF) 서서히 비워짐
    # 핫스팟의 위치/개수/세기는 에피소드마다 시드로 무작위 선택 (bg_traffic.sample_hotspots). 같은 시드면 같은 시나리오
    # 에피소드 안에서는 핫스팟 위치가 고정이고, ON/OFF 시점만 계속 바뀜
    P.bgEnable = True                      # False면 배경 트래픽 없음 (기존 결과와 완전히 같음)
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
    P.bgFlows = []                         # 아래 3개는 sample_hotspots가 채움 (직접 쓰지 않음)
    P.bgOnRate = []
    P.bgSeed = 0

    return P
