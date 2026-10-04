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
    P.queueMax = 100                       # 링크별 큐 최대 용량 (packets)
    P.linkCapacity = 10                    # ISL 대역폭 (packets/step)
    P.linkDelay = np.array([7, 7, 2, 2])   # 링크 지연 [상 하 좌 우] (step)
    P.processingDelay = 0                  # 처리 지연 (step)

    # ---- 패킷 ----
    P.ttlInit = 20                         # TTL 초기값 (잔여 홉)
    P.deadline = 100                       # 기한 (step)
    P.packetSize = 160                     # 패킷 크기 (Byte)

    # ---- B 라우팅 (Liu et al. 단순화) ----
    P.X = 0.5                              # Idle / Relatively Busy 경계
    P.Y = 0.8                              # Relatively Busy / Busy 경계
    P.k = 0.5                              # 가중치 (1: V만, 0: N만)

    # ---- 실험 ----
    P.genRate = 60                         # 1초마다 생성하는 패킷 수 (일정 간격)
    P.epsilonList = [0, 0.1]               # 무작위 선택 확률 (0: 성능 측정용, 0.1: 데이터 수집용)
    P.simTime = 600000                     # 총 시뮬레이션(패킷 생성) 시간 (step = 10분)
    P.maxDrainTime = 500                   # 생성 종료 후 남은 패킷 처리 최대 step [설정]
    P.randomSeed = 1                       # 난수 시드                             [설정]
    P.stepTime = 1e-3                      # 1 step = 1 ms (초 단위)

    # ---- 애니메이션 ----
    P.animDuration = 200                   # 애니메이션에 담을 step 수             [설정]
    P.animFrameInterval = 2                # 몇 step마다 한 프레임                 [설정]
    return P
