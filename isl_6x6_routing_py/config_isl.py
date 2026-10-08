# 설정값 모음 - 시뮬레이션에 쓰이는 모든 변수값을 여기서 정함
# (값 바꾸려면 여기서 수정하면 됩니다!)
#
from types import SimpleNamespace

import numpy as np

from config_bg import apply_bg, config_bg


def config_isl():
    # ISL 2D Grid 정적 라우팅 시뮬레이션 설정값
    P = SimpleNamespace()

    # ---- 네트워크 구조 ----
    P.numPlanes = 6                        # 궤도면 수 (좌/우)
    P.satsPerPlane = 6                     # 궤도면당 위성 수 (상/하)
    P.srcSat = np.array([0, 0])            # 출발 위성 (p,s)
    P.dstSat = np.array([5, 5])            # 도착 위성 (p,s)
    P.queueMax = 200                       # 링크별 큐 최대 용량 (packets) [배경 트래픽 실험: 100 -> 200]
    P.linkCapacity = 5                     # ISL 대역폭 (packets/step) [배경 트래픽 실험: 10 -> 5]
    P.linkDelay = np.array([7, 7, 2, 2])   # 링크 지연 [상 하 좌 우] (step)
    P.processingDelay = 0                  # 처리 지연 (step)

    # ---- 패킷 ----
    P.ttlInit = 20                         # TTL 초기값 (잔여 홉)
    P.deadline = 90                        # 기한 (step) [배경 트래픽 실험: 100 -> 90]
    P.packetSize = 160                     # 패킷 크기 (Byte)

    # ---- 라우팅 알고리즘 ----
    P.routeName = 'routeB'                 # 'routeA': 최단 경로 (부하 무시), 'routeB': 부하 고려 (Liu 단순화)
                                           # 결과 저장 폴더 이름으로도 쓰임 (routeA / routeB / routeC)

    # ---- B 라우팅 (링크 부하 반영, Liu et al. 단순화) ----
    P.X = 0.5                              # Idle / Relatively Busy 경계
    P.Y = 0.8                              # Relatively Busy / Busy 경계
    P.k = 0.5                              # 가중치 (1: V만, 0: N만)

    # ---- 실험 ----
    P.genRate = 60                         # 1초마다 생성하는 패킷 수 (일정 간격)
    P.epsilonList = [0, 0.1]               # 무작위 선택 확률 (0: 성능 측정용, 0.1: 데이터 수집용), 무작위면 라우팅이 고른 것과 다른 방향
    P.simTime = 600000                     # 총 시뮬레이션(패킷 생성) 시간 (step = 10분)
    P.maxDrainTime = 500                   # 생성 종료 후 남은 패킷 처리 최대 step [설정]
    P.randomSeed = 1                       # ε 무작위 선택 시드 (config_bg.py apply_bg가 배경 시드와 같게 덮어씀)
    P.stepTime = 1e-3                      # 1 step = 1 ms (초 단위)

    # ---- 노드 기록 (node_log CSV: 노드 기준 상태) ----
    P.nodeLogEnable = True                 # False면 node_log 저장 안 함
    P.nodeLogInterval = 100                # 몇 step마다 노드 36개를 1줄씩 기록 (작을수록 파일이 커짐) [설정]

    # ---- 애니메이션 ----
    P.animDuration = 3000                  # 애니메이션에 담을 step 수 (3초)       [설정]
    P.animFrameInterval = 10               # 몇 step마다 한 프레임 (300장)         [설정]

    # ---- 배경 트래픽: config_bg.py에서 관리 (부하 단계, 시드, 실험 on/off) ----
    B = config_bg()
    apply_bg(P, B, B.mainLevel, B.mainSeed)
    return P
