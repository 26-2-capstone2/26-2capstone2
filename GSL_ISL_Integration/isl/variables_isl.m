% 변수 정리 - 이 시뮬레이션에서 쓰는 모든 변수를 종류별로 모아 둔 주석 파일
% 형식 = 변수: 코드 이름 = 값
% 
% ---------------- 1. 위성망 네트워크 환경 변수 (Topology) ----------------
% 궤도면 수: P.numPlanes = 6
% 궤도면 당 위성 수: P.satsPerPlane = 6
% 시뮬레이션 단위 시간: P.stepTime = 1 ms (= 1 step)
% 궤도 내 링크 거리: (코드 없음) 1970 km -> 상/하 지연 7 step의 근거
% 궤도 간 링크 거리: (코드 없음) 500 km -> 좌/우 지연 2 step의 근거
%
% ---------------- 2. 위성 노드 변수 ----------------
% 위성 식별자: (p,s) = (0,0) ~ (5,5)   * 코드 내부는 +1 해서 1~6
% 최대 큐 용량: P.queueMax = 100 packets (링크별)
% 현재 큐 길이: queueLen = 0 ~ 100
% 처리 지연: P.processingDelay = 0 step
%
% ---------------- 3. 링크 ----------------
% ISL 대역폭: P.linkCapacity = 10 packets/step
% 동일 궤도면 내 지연 (상/하): P.linkDelay(1:2) = 7 step
% 인접 궤도면 간 지연 (좌/우): P.linkDelay(3:4) = 2 step
% 방향 번호: nextDir = 1 상, 2 하, 3 좌, 4 우
%
% ---------------- 4. 패킷 ----------------
% 패킷 id: packet_id (0부터 +1)
% 패킷 Size: P.packetSize = 160 Byte
% 1초마다 생성하는 패킷 수: P.genRate = 60
% 현재 위성: curP, curS
% 출발 위성: P.srcSat = (0,0)
% 도착 위성: P.dstSat = (5,5)
% TTL: P.ttlInit = 20
% 현재 홉 수: hops
% 생성 시각: genTime
% 기한: P.deadline = 100 step
%
% ---------------- 5. 라우팅 알고리즘 B ----------------
% 링크 점유율: L = (k*V + (1-k)*N) / Q
% 링크 부하: V = 보내려는 링크의 큐 길이
% 이웃 부하: N = 다음 위성의 링크 큐 길이 평균
% 링크 큐 최대 용량: Q = P.queueMax = 100
% 가중치: P.k = 0.5 [추천값]
% 임계값 X: P.X = 0.5 [추천값]
% 임계값 Y: P.Y = 0.8 [추천값]
% 주 경로: primaryDir (좌/우 방향)
% 대체 경로: altDir (상/하 방향)
% 선택 유형: choiceType = 1 주, 2 대체, 3 우회, 4 무작위
%
% ---------------- 6. 실험 설정 ----------------
% 총 시뮬레이션 시간: P.simTime = 600000 step (10분) [설정]
% 남은 패킷 처리 한도: P.maxDrainTime = 500 step [설정]
% 무작위 선택 확률: P.epsilonList = 0 (성능 측정용), 0.1 (데이터 수집용)
% 난수 시드: P.randomSeed = 1 [설정]
% 애니메이션 길이: P.animDuration = 200 step [설정]
% 애니메이션 간격: P.animFrameInterval = 2 step [설정]
% 결과 저장 경로: saveDir = C:\Users\eun\Desktop\capstone_isl\baseline (main_isl.m 맨 아래)
%
% ---------------- 7. 손실 / 결과 (패킷 기록 result) ----------------
% 기한 내 도착: result = 1   (코드 안에서는 status)
% 목적지 기한 초과: result = 2
% 중간 기한 초과: result = 3
% 큐 오버플로: result = 4
% TTL 만료: result = 5
%
% ---------------- 8. 성능 평가 지표 ----------------
% Average Latency: avgLatency_ms
% Packet Loss Rate: lossRate
% Throughput: throughput_Mbps
% On-time Delivery Rate: onTimeRate
% Consecutive Packet Loss Length: maxConsecLoss
% Route Change Count: routeChanges
% Average Hop Count: avgHops
%
% ---------------- 9. 강화학습용 결정 기록 (decision_log CSV 열) ----------------
% 결정 시점: step
% 패킷 id: packet_id
% 홉 번호: hop
% 현재 위성: cur_p, cur_s
% 4개 링크 큐 길이: q_up, q_down, q_left, q_right
% 4개 링크 점유율: L_up, L_down, L_left, L_right
% 4개 이웃 부하: N_up, N_down, N_left, N_right
% 남은 거리: rem_dp, rem_ds
% 남은 기한: rem_deadline
% TTL: ttl
% 고른 방향: action
% 선택 유형: choice_type
% 큐 진입 성공 여부: enqueued
% * 없는 방향(Grid 끝)은 -1
