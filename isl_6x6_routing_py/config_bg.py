# 배경 트래픽 설정 - 배경 흐름, 부하 단계(낮음/중간/높음), 시드, 실험 on/off를 한 곳에서 관리
# (배경 관련 값은 여기서만 수정하면 됩니다!)
#
# 배경 트래픽 = 주 흐름이 아닌 혼잡용 패킷. RL/B가 제어하지 않는 고정 경로로 보냄
#   main_isl.py        : 아래 "실행 1회" 단계·시드로 1번 자세히 실행 (애니메이션, 로그, 그림)
#   run_experiments.py : 아래 "여러 시드 실험" on/off대로 부하 단계 x 시드를 돌려 평균 ± 편차 표를 만듦
from types import SimpleNamespace


def config_bg():
    B = SimpleNamespace()

    # ---- 배경 흐름 (모든 부하 단계 공통) ----
    B.flows = [((0, 0), (5, 0)), ((2, 0), (5, 0)),     # (출발 (p,s), 도착 (p,s))
               ((5, 0), (5, 5)), ((5, 2), (5, 5))]     # 주 흐름 기본 경로(위 줄 -> 오른쪽 열)와 겹침
    B.onMean = 500                         # ON 평균 길이 (step, 지수분포)
    B.offMean = 500                        # OFF 평균 길이 (step, 지수분포)
    B.ttl = 20                             # 배경 패킷 TTL (배경은 기한 없음)
    B.poolSize = 20000                     # 동시에 존재할 수 있는 배경 패킷 수

    # ---- 부하 단계: ON일 때 흐름별 전송률 (packets/step) ----
    # 링크 용량 P.linkCapacity = 5. 두 흐름이 합쳐지는 링크에 2 x 전송률이 몰림
    #   2.5 이하: 합쳐도 5 이하라 혼잡 없음 / 3.0부터 두 흐름이 동시에 켜질 때 넘침 / 5 이상: 흐름 하나로도 넘침
    # 2분 실행 기한 내 도착률 참고값 (시드 101 기준): 3.5 약 85%, 4.5 약 79%, 5.5 약 51%, 6.5 약 47%
    # 손실이 충분히 생기도록 팀원 노션 원래 값 5.5를 '높음'으로 둠
    B.levels = {
        'none':    0.0,                    # 배경 없음 (혼잡 없는 기준)
        'low':     3.5,                    # 낮음
        'mid':     4.5,                    # 중간
        'high':    5.5,                    # 높음 (팀원 노션 원래 값)
        'extreme': 6.5,                    # 매우 높음
    }
    B.levelNames = {'none': '없음', 'low': '낮음', 'mid': '중간', 'high': '높음', 'extreme': '매우 높음'}

    # ---- 시드 (배경 ON/OFF 패턴, ε 무작위 선택에 같이 사용) ----
    B.trainSeeds = list(range(1, 11))      # 학습용 (RL 데이터 수집)  1 ~ 10
    B.evalSeeds = list(range(101, 111))    # 평가용 (성능 비교)       101 ~ 110  * 학습에 쓰지 말 것
    B.baseSeeds = 1001 # 최종 비교 지표용 1001 

    # ---- 실행 1회 (main_isl.py) ----
    B.mainLevel = 'high'                   # 부하 단계 (none/low/mid/high/extreme)
    B.mainSeed = 1001                      # 배경 시드 (1~10/101~110/1001)

    # ---- 여러 시드 실험 (run_experiments.py) on/off ----
    B.runLevels = {                        # True인 부하 단계만 실행
        'none':    False,
        'low':     True,
        'mid':     True,
        'high':    True,
        'extreme': False,
    }
    B.runEval = True                       # 평가: ε = 0, 평가용 시드 -> 평균 ± 편차 표, 그래프
    B.runTrain = False                     # 학습 데이터 수집: ε = trainEpsilon, 학습용 시드 -> decision_log, packet_log 저장
                                           #   (실행 1번당 decision_log 약 30 MB)
    B.trainEpsilon = 0.1                   # 학습 데이터 수집 때 무작위 선택 확률
    B.numSeeds = 10                        # 시드 목록 앞에서부터 몇 개 쓸지 (빨리 볼 때는 줄이기)
    B.numWorkers = 6                       # 동시에 돌릴 실행 수 (CPU 코어 수보다 작게, 이 PC는 8코어)
    return B


def apply_bg(P, B, level, seed):
    # 설정 P에 배경 부하 단계와 시드를 넣음 (run_isl_sim이 쓰는 P.bg* 값)
    rate = B.levels[level]
    P.bgLevel = level
    P.bgEnable = rate > 0
    P.bgFlows = B.flows
    P.bgOnRate = [rate] * len(B.flows)
    P.bgOnMean = B.onMean
    P.bgOffMean = B.offMean
    P.bgTtl = B.ttl
    P.bgPoolSize = B.poolSize
    P.bgSeed = seed
    P.randomSeed = seed   # ε 무작위 선택도 같은 시드 (실행 이름 routeB_단계_시드의 시드 하나로 결과가 정해지게)
    return P
