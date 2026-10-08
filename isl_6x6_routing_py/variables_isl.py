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
# 기한: P.deadline = 90 step [배경 트래픽 실험: 100 -> 90]
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
# 선택 유형: choiceType = 1 주, 2 대체, 3 우회, 4 무작위 (확률 ε로 route_B가 고른 방향을 뺀 나머지 중 하나)
#
# ---------------- 5-1. 배경 트래픽 (혼잡용, 고정 경로, 지표 계산에서 제외) - 값은 config_bg.py ----------------
# 배경 흐름 (출발 -> 도착): B.flows = (0,0)->(5,0), (2,0)->(5,0), (5,0)->(5,5), (5,2)->(5,5)
# ON / OFF 평균 길이: B.onMean = 500 step, B.offMean = 500 step (지수분포)
# 배경 TTL: B.ttl = 20 (배경은 기한 없음) / 동시 배경 패킷 최대 수: B.poolSize = 20000
# 부하 단계 (ON일 때 흐름별 packets/step): B.levels = 없음 0, 낮음 3.5, 중간 4.5, 높음 5.5, 매우 높음 6.5
# 시드: 학습용 B.trainSeeds = 1~10, 평가용 B.evalSeeds = 101~110 (배경 패턴 + ε 무작위 선택에 같이 사용)
# main_isl.py 실행 1회: B.mainLevel = 'high' (5.5), B.mainSeed = 1001
# run_experiments.py on/off: B.runLevels (단계별), B.runEval (평가), B.runTrain (학습 데이터 수집),
#                            B.trainEpsilon = 0.1, B.numSeeds = 10, B.numWorkers = 6
# 시뮬레이션 안에서 쓰는 이름 (apply_bg가 넣어 줌): P.bgLevel, P.bgEnable, P.bgFlows, P.bgOnRate, P.bgOnMean,
#                                                  P.bgOffMean, P.bgSeed, P.bgTtl, P.bgPoolSize
# 배경 경로: 목적지 쪽 좌/우 먼저, 같은 열이면 상/하 (부하를 보지 않음)
# 배경 결과 (metrics_summary): bgGenerated, bgDelivered, bgOverflow, bgTtlExpired, bgPoolFull
#
# ---------------- 6. 실험 설정 ----------------
# 총 시뮬레이션 시간: P.simTime = 600000 step (10분) [설정]
# 남은 패킷 처리 한도: P.maxDrainTime = 500 step [설정]
# 무작위 선택 확률: P.epsilonList = 0 (성능 측정용), 0.1 (데이터 수집용) - 무작위면 route_B와 다른 방향만 고름
# ε 무작위 선택 시드: P.randomSeed = 배경 시드와 같음 (apply_bg가 설정)
# 애니메이션 길이: P.animDuration = 3000 step (3초) [설정]
# 애니메이션 간격: P.animFrameInterval = 10 step (300장) [설정]
# 결과 저장 경로: SAVE_ROOT = C:\Users\eun\Desktop\capstone_isl\baseline_py (save_results.py 맨 위)
#   그 아래 P.routeName \ (baseline / train / evaluation) \ 라우팅알고리즘_부하단계_시드
# 라우팅 알고리즘 이름: P.routeName = 'routeB' (결과 폴더 이름)
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
# Consecutive Packet Loss Length: maxConsecLoss
# Route Change Count: routeChanges
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
