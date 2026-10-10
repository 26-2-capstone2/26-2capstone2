# 변수 정리 - 이 시뮬레이션에서 쓰는 모든 변수를 종류별로 모아 둔 주석 파일
# 형식 = 변수: 코드 이름 = 값
# 
# ---------------- 1. 위성망 네트워크 환경 변수 (Topology) ----------------
# 궤도면 수: P.numPlanes = 6
# 궤도면 당 위성 수: P.satsPerPlane = 6
# 시뮬레이션 단위 시간: P.stepTime = 1 ms (= 1 step)
# 궤도 내 링크 거리: (코드 없음) 1970 km -> 상/하 지연 7 step의 근거
# 궤도 간 링크 거리: (코드 없음) 500 km -> 좌/우 지연 2 step의 근거
#
# ---------------- 2. 위성 노드 변수 ----------------
# 위성 식별자: (p,s) = (0,0) ~ (5,5)   * 파이썬은 문서 좌표 그대로 0~5 사용
# 최대 큐 용량: P.queueMax = 200 packets (링크별) [배경 트래픽 실험: 100 -> 200]
# 현재 큐 길이: queueLen = 0 ~ 200
# 처리 지연: P.processingDelay = 0 step
#
# ---------------- 3. 링크 ----------------
# ISL 대역폭: P.linkCapacity = 5 packets/step [배경 트래픽 실험: 10 -> 5]
# 동일 궤도면 내 지연 (상/하): P.linkDelay[0:2] = 7 step
# 인접 궤도면 간 지연 (좌/우): P.linkDelay[2:4] = 2 step
# 방향 번호: nextDir = 1 상, 2 하, 3 좌, 4 우
#
# ---------------- 4. 패킷 ----------------
# 패킷 id: packet_id (0부터 +1)
# 패킷 Size: P.packetSize = 160 Byte
# 1초마다 생성하는 패킷 수: P.genRate = 60
# 현재 위성: curP, curS
# 출발 위성: P.srcSat = (0,0)
# 도착 위성: P.dstSat = (5,5)
# TTL: P.ttlInit = 20
# 현재 홉 수: hops
# 생성 시각: genTime
# 기한: P.deadline = 70 step [배경 트래픽 실험: 100 -> 70, 팀원 설정]
#
# ---------------- 5-0. 라우팅 알고리즘 선택 ----------------
# 라우팅 알고리즘: P.routeName = 'routeA' (최단 경로) / 'routeB' (부하 고려)  * 결과 폴더 이름으로도 쓰임
# A 최단 경로 (route_A.py): 링크 지연 합이 가장 작은 경로로만 보냄 (Dijkstra, 큐는 안 봄)
#   목적지까지 최소 지연: G.distToDst (처음 한 번 계산), 동점이면 우 > 좌 > 하 > 상 (좌/우 먼저)
#   choiceType은 항상 1, decision_log의 L, N은 기록용 (결정에는 안 씀)
#
# ---------------- 5. 라우팅 알고리즘 B ----------------
# 링크 점유율: L = (k*V + (1-k)*N) / Q
# 링크 부하: V = 보내려는 링크의 큐 길이
# 이웃 부하: N = 다음 위성의 링크 큐 길이 평균
# 링크 큐 최대 용량: Q = P.queueMax = 200
# 가중치: P.k = 0.5 [추천값]
# 임계값 X: P.X = 0.5 [추천값]
# 임계값 Y: P.Y = 0.8 [추천값]
# 주 경로: primaryDir (좌/우 방향)
# 대체 경로: altDir (상/하 방향)
# 선택 유형: choiceType = 1 주, 2 대체, 3 우회, 4 무작위 (확률 ε로 갈 수 있는 방향 중 하나, 라우팅이 고른 방향일 수도 있음)
#
# ---------------- 5-1. 배경 트래픽 (송신 큐 핫스팟, 지표 계산에서 제외) - bg_traffic.py ----------------
# 핫스팟 = 위성 하나의 한 방향 송신 큐가 과부하 (그 위성 -> 그 방향 이웃으로 가는 1홉 배경 흐름)
# 사용 여부: P.bgEnable = True
# 시작 시드: P.bgScenarioSeed = 1 (에피소드 e는 시드 + e, None이면 무작위 / python main_isl.py 7 처럼 지정 가능)
# 핫스팟 개수: P.bgNumMin ~ P.bgNumMax = 2 ~ 5 (에피소드마다 무작위)
# 핫스팟 세기: P.bgLoadMin ~ P.bgLoadMax = 0.7 ~ 2.0 x 링크 용량 (에피소드마다 무작위)
# 막힘 기준: P.bgBlockLoad = 1.8 (이 이상이면 막힌 큐로 보고, 그래도 도착할 길이 있는 시나리오만 사용)
# 관련 큐 가중치: P.bgRelWeight = 3.0 (출발-도착 사각형 안, 목적지 쪽 방향 큐를 3배 더 잘 뽑음)
# 관련 큐 최소 개수: P.bgMinRelevant = 1
# ON / OFF 평균 길이: P.bgOnMean = 150 step, P.bgOffMean = 750 step (지수분포, ON일 때 Poisson 생성)
# 배경 TTL: P.bgTtl = 20 (배경은 기한 없음) / 동시 배경 패킷 최대 수: P.bgPoolSize = 20000
# 자동으로 채워지는 값 (sample_hotspots): P.bgFlows, P.bgOnRate, P.bgSeed
# 배경 경로: XY 경로 (목적지 쪽 좌/우 먼저, 같은 열이면 상/하, 부하를 보지 않음)
# 배경 결과 (metrics_summary): bgGenerated, bgDelivered, bgOverflow, bgTtlExpired, bgSrcDrop
# 시나리오 기록: results\bg_scenario.csv (에피소드, 시드, 핫스팟 위치와 방향, 세기, 관련 여부)
#
# ---------------- 6. 실험 설정 ----------------
# 에피소드 길이: P.simTime = 30000 step (30초), 에피소드마다 큐가 비어 있는 상태로 시작 [설정]
# 에피소드 개수: P.numEpisodes = 20 (총 10분) [설정]
# 남은 패킷 처리 한도: P.maxDrainTime = 500 step [설정]
# 무작위 선택 확률: P.epsilonList = 0 (성능 측정용), 0.1 (데이터 수집용)
# ε 무작위 선택 시드: P.randomSeed = 1 (에피소드 e는 randomSeed + e) [설정]
# 애니메이션 길이: P.animDuration = 200 step (0.2초, 첫 에피소드만) [설정]
# 애니메이션 간격: P.animFrameInterval = 2 step (100장) [설정]
# 결과 저장 경로: (홈 폴더)\isl_saved_runs\날짜_시분 (환경변수 ISL_SAVE_ROOT로 바꿀 수 있음, main_isl.py 맨 아래)
# 라우팅 알고리즘 이름: P.routeName = 'routeA' / 'routeB'
#
# ---------------- 7. 손실 / 결과 (패킷 기록 result) ----------------
# 기한 내 도착: result = 1   (코드 안에서는 status)
# 목적지 기한 초과: result = 2
# 중간 기한 초과: result = 3
# 큐 오버플로: result = 4
# TTL 만료: result = 5
#
# ---------------- 8. 성능 평가 지표 ----------------
# Average Latency: avgLatency_ms
# Packet Loss Rate: lossRate
# Throughput: throughput_Mbps
# On-time Delivery Rate: onTimeRate
# Consecutive Packet Loss Length: maxConsecLoss (에피소드 경계에서 끊어서 셈)
# Route Change Count: routeChanges (에피소드 경계에서 끊어서 셈)
# Average Hop Count: avgHops
#
# ---------------- 9. 강화학습용 결정 기록 (decision_log CSV 열) ----------------
# 결정 시점: step
# 패킷 id: packet_id
# 홉 번호: hop
# 현재 위성: cur_p, cur_s
# 4개 링크 큐 길이: q_up, q_down, q_left, q_right
# 4개 링크 점유율: L_up, L_down, L_left, L_right
# 4개 이웃 부하: N_up, N_down, N_left, N_right
# 남은 거리: rem_dp, rem_ds
# 남은 기한: rem_deadline
# TTL: ttl
# 고른 방향: action
# 선택 유형: choice_type
# 큐 진입 성공 여부: enqueued
# * 없는 방향(Grid 끝)은 -1
#
# ---------------- 10. 노드 기록 (node_log CSV 열) - 노드 기준, P.nodeLogInterval step마다 노드 1개 = 1줄 ----------------
# 사용 여부 / 기록 간격: P.nodeLogEnable = True, P.nodeLogInterval = 100 step
# 기록 시각, 노드: step, p, s
# 링크 큐 길이 (기록 시각, 전송 후): q_up, q_down, q_left, q_right
# 링크 큐 최대 길이 (직전 기록 이후, 전송 직전): qmax_up, qmax_down, qmax_left, qmax_right
# 노드 큐 안 패킷 수 (기록 시각): main_queued (주 흐름), bg_queued (배경)
# 큐 안 주 흐름 패킷의 남은 기한 최솟값: min_rem_deadline (-1: 주 흐름 패킷 없음)
# 직전 기록 이후 보낸 수: main_sent, bg_sent
# 직전 기록 이후 큐 오버플로: main_overflow, bg_overflow
# 직전 기록 이후 이 노드에서 끝난 주 흐름: main_late_mid (중간 기한 초과), main_ttl_expired, main_on_time, main_late_dst (목적지 노드만)
# * 없는 방향(Grid 끝)은 -1, 보기: python show_node.py [p s [ε]]
