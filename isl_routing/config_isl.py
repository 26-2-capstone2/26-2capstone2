# 설정값 모음 - 시뮬레이션에 쓰이는 모든 변수값을 여기서 정함
# (값 바꾸려면 여기서 수정하면 됩니다!)
#
import os
from types import SimpleNamespace

import numpy as np


# 혼잡 단계별 배경 트래픽 값 (P.bgLevel로 고름): 핫스팟 개수 범위, ON/OFF 평균 길이 (step)
# 나머지 배경 값(세기 0.7~2.0배, 막힘 기준 1.8, 주 흐름 쪽 가중치 3 등)은 모든 단계에서 같음
# 켜짐 + 꺼짐 = 900 step으로 맞춰 주기는 같고 켜진 시간 비율만 커짐
BG_LEVELS = {
    'base':   dict(bgNumMin=2, bgNumMax=5, bgOnMean=150, bgOffMean=750),   # 기본, 켜진 시간 약 1/6 (평상시)
    'high':   dict(bgNumMin=3, bgNumMax=6, bgOnMean=300, bgOffMean=600),   # 높음, 약 1/3 (붐비는 시간대)
    'severe': dict(bgNumMin=4, bgNumMax=7, bgOnMean=450, bgOffMean=450),   # 매우 높음, 약 1/2 (피크, 이벤트 상황)
    'extreme': dict(bgNumMin=4, bgNumMax=7, bgOnMean=450, bgOffMean=450),  # 'event' 전용 최악 상황 (hotspot 방식에서는 severe와 같음)
}


# 혼잡 사건 방식(P.bgMode = 'event', sim/bg_event.py)의 단계별 값 (step): 지역 핫스팟 발생 간격 평균, 지속 시간 평균
# 지속 평균 2.5초: 실제 망의 혼잡은 짧은 버스트(Back-Pressure 논문 평균 1초)보다 길게 이어지는 경우가 많아 늘림
# 발생 간격: 30초 에피소드에서 동시에 걸린 지역이 '항상 한 곳(약 1개) / 여러 곳(약 2개) / 최악(약 4개)'이 되게 정한 값
# (처음 정한 base 5000은 빼고 한 단계씩 올림: 이전 high -> base, 이전 severe -> high, severe는 최악 상황으로 새로 추가)
EVENT_LEVELS = {
    'base':   dict(evIntervalMean=2500, evDurationMean=2500, evLoadMin=0.5, evLoadMax=1.5, evNbrRatio=0.5, failEnable=False),   # 30초에 핫스팟 약 12번, 동시 약 1개 지역
    'high':   dict(evIntervalMean=1250, evDurationMean=2500, evLoadMin=0.5, evLoadMax=1.5, evNbrRatio=0.5, failEnable=False),   # 약 24번, 동시 약 2개
    'severe': dict(evIntervalMean=625, evDurationMean=2500, evLoadMin=0.5, evLoadMax=1.5, evNbrRatio=0.5, failEnable=False),    # 약 48번, 동시 약 4개
    # extreme (테스트 6): 혼잡 세기 강화 + 링크 장애 (DTAR 장애 시나리오). 동시 약 5개 지역, 세기 1.0~2.0배, 이웃 0.7배
    'extreme': dict(evIntervalMean=500, evDurationMean=2500, evLoadMin=1.0, evLoadMax=2.0, evNbrRatio=0.7, failEnable=True),
}
EV_TIME_KEYS = ('evIntervalMean', 'evDurationMean')   # ISL_EV_TIME_SCALE을 곱하는 값 (시간 값만)


def apply_bg_level(P, level):
    # 혼잡 단계 이름으로 위 표의 값을 P에 덮어씀 (config_isl 끝과 main_isl 실행 인자에서 사용)
    if level not in BG_LEVELS:
        raise ValueError(f'혼잡 단계는 {list(BG_LEVELS)} 중 하나: {level}')
    P.bgLevel = level
    for k, v in BG_LEVELS[level].items():
        setattr(P, k, v)
    scale = float(os.environ.get('ISL_EV_TIME_SCALE', '1'))   # 핫스팟 지속, 간격을 같은 비율로 줄임 (0.4면 지속 1초, 동시 핫스팟 수는 그대로)
    for k, v in EVENT_LEVELS[level].items():
        setattr(P, k, max(1, round(v * scale)) if k in EV_TIME_KEYS else v)
    return P


def config_isl():
    # ISL 2D Grid 라우팅 시뮬레이션 설정값
    P = SimpleNamespace()

    # ---- 네트워크 구조 ----
    P.numPlanes = 6                        # 궤도면 수 (좌/우)
    P.satsPerPlane = 6                     # 궤도면당 위성 수 (상/하)
    P.srcSat = np.array([0, 0])            # 출발 위성 (p,s)
    P.dstSat = np.array([5, 5])            # 도착 위성 (p,s)
    # 망 구조: 'grid' (지금 6x6), 'grid:8x8' (크기 지정), 'iridium', 'starlink', 'starlink:12x12' (축소판) - sim/topology.py
    #   실행할 때 환경 변수로 바꿈: ISL_TOPOLOGY=iridium python main_isl.py  (기본은 'grid' = 아래 6x6 값 그대로)
    #   grid가 아니면 크기, 원형 연결, 링크 지연, 출발/도착, 기한, TTL을 그 구조에 맞게 덮어씀 (config 끝에서 적용)
    P.topology = os.environ.get('ISL_TOPOLOGY', 'grid')
    P.queueMax = 200                       # 링크별 큐 최대 용량 (packets)
    P.linkCapacity = 5                    # ISL 대역폭 (packets/step)
    P.linkDelay = np.array([7, 7, 2, 2])   # 링크 지연 [상 하 좌 우] (step)
    P.processingDelay = 0                  # 처리 지연 (step)

    # ---- 패킷 ----
    P.ttlInit = 20                         # TTL 초기값 (잔여 홉)
    P.deadline = 70                       # 기한 (step)
    P.packetSize = 160                     # 패킷 크기 (Byte)

    # ---- 연속 손실 ----
    P.burstMinLen = 3                      # 패킷 번호 순서로 손실이 이 개수 이상 이어지면 '연속 손실' 1번 (burst_loss.py)

    # ---- B 라우팅 (DRA, Ekici et al. 2001) ----
    P.draThreshold = 0.5                   # 송신 큐가 queueMax의 이 비율 이상이면 '혼잡' -> 보조 방향 사용 (0.5 = 100 packets)
    P.k = 0.5                              # decision_log의 링크 점유율 L 계산용 가중치 (1: V만, 0: N만, 결정에는 안 씀)

    # ---- 라우팅 알고리즘 선택 ----
    # 'routeA': 정적 다익스트라 (링크 지연만, 부하 무시 - 기준선)
    # 'routeB': DRA (Ekici et al. 2001, 자기 송신 큐만 보고 주/보조 방향 선택)
    # 'routeC': 강화학습 (학습된 모델이 필요해서 eval_routes.py, rl/train_rl.py, main_isl.py 실행 인자로 돌림)
    P.routeName = 'routeB'                 # 실행할 라우팅 (기본 B, A와 같이 보려면 ['routeA', 'routeB']). 비교할 라우팅 목록 (ε = 0으로 하나씩 실행). 하나만 돌리려면 'routeB'처럼 문자열
    P.collectRoute = 'routeB'              # ε > 0 (강화학습 데이터 수집) 실행에 쓰는 라우팅

    # ---- 실험 ----
    P.genRate = 60                         # 1초마다 생성하는 패킷 수 (일정 간격)
    P.numFlows = int(os.environ.get('ISL_NUM_FLOWS', '1'))   # 주 흐름 수 (흐름마다 초당 genRate개). 1: 기존 (0,0) -> (5,5)만, 3: 기존 + 무작위 2개 (sim/flows.py)
    P.flowDelayMin, P.flowDelayMax = 30, 45   # 무작위 흐름의 출발 -> 도착 최소 지연 범위 (step, 주 흐름은 45)
    P.epsilonList = [0, 0.1]               # 무작위 선택 확률 (0: 성능 측정용, 0.1: 데이터 수집용)
    P.simTime = 10000                      # 에피소드 1개의 길이 (step = 10초). 에피소드마다 큐가 비어 있는 상태로 시작
                                           #   학습 안정화 계획: 에피소드당 결정 약 7천~8천 번으로 줄여 학습 곡선을 촘촘하게 봄
    P.numEpisodes = 20                     # 에피소드 개수 = 최종 평가 시드 1~20 (총 시뮬레이션 = simTime x numEpisodes)
    P.maxDrainTime = 500                   # 생성 종료 후 남은 패킷 처리 최대 step [설정]
    P.randomSeed = 1                       # 난수 시드                             [설정]
    P.stepTime = 1e-3                      # 1 step = 1 ms (초 단위)

    # ---- 애니메이션 ----
    P.animDuration = 200                   # 애니메이션에 담을 step 수             [설정]
    P.animFrameInterval = 2                # 몇 step마다 한 프레임                 [설정]

    # ---- 노드 기록 (node_log) ----
    P.nodeLogEnable = True                 # False면 노드 기록 안 함 (node_log CSV / node 그림 생략)
    P.nodeLogInterval = 100                # 몇 step마다 노드별 1줄 기록 (100 step = 0.1초)

    # ---- 배경 트래픽 (송신 큐 핫스팟) ----
    # 핫스팟 = 위성 하나의 한 방향 송신 큐가 과부하. 켜지면(ON) 큐가 차서 패킷이 버려지고, 꺼지면(OFF) 서서히 비워짐
    # 핫스팟의 위치/개수/세기는 에피소드마다 시드로 무작위 선택 (bg_traffic.sample_hotspots). 같은 시드면 같은 시나리오
    # 에피소드 안에서는 핫스팟 위치가 고정이고, ON/OFF 시점만 계속 바뀜
    P.bgEnable = True                      # False면 배경 트래픽 없음 (기존 결과와 완전히 같음)
    P.bgMode = 'event'                     # 'event': 기본 부하 + 지역 핫스팟이 무작위로 생겼다 사라짐 (sim/bg_event.py, 위 EVENT_LEVELS)
                                           # 'hotspot': 기존 방식, 핫스팟 위치 고정 + 켜짐/꺼짐 (bg_traffic.py, 위 BG_LEVELS)
    P.bgBaseMin, P.bgBaseMax = 0.1, 0.4    # 'event' 기본 부하: 모든 링크에 링크 용량의 0.1~0.4배 (링크마다 에피소드 시작에 정함)
    P.evLoadMin, P.evLoadMax = 0.5, 1.5    # 'event' 지역 핫스팟: 중심 위성의 송신 링크마다 기본 부하에 더하는 세기 (용량의 배수)
    P.evNbrRatio = 0.5                     # 'event' 이웃 위성의 송신 링크에는 위 세기의 이 비율만큼 더함 (지역 혼잡)
    P.evCorridor = 1.0                     # 'event' 출발 -> 도착 직선에서 이 칸 수 이내 위성이 '주 흐름이 지나는 지역' (bgRelWeight배 더 자주)
    P.failEnable = False                   # 링크 장애 (단계 표 EVENT_LEVELS의 failEnable로 켬, extreme만). 끊긴 링크는 양방향 모두 끊김
    P.failDownFrac = 0.02                  # 평균적으로 끊겨 있는 링크 비율 (DTAR 장애 시나리오 2%)
    P.failDurationMean = 2000              # 장애 지속 평균 (step, 지수분포)
    P.evSafeLoad = 1.0                     # 'event' 안전장치: 부하 합이 용량의 이 배수 이상인 링크를 모두 빼고도 출발 -> 도착 길이 있어야 핫스팟을 만듦
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
    P.bgLevel = 'base'                     # 혼잡 단계: 'base', 'high', 'severe' (위 BG_LEVELS 값으로 핫스팟 개수, ON/OFF를 덮어씀)
    apply_bg_level(P, P.bgLevel)

    if P.topology != 'grid':
        from sim.topology import apply_topology
        apply_topology(P, P.topology)

    return P
