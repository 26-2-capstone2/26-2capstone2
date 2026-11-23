# 변수 정리

이 시뮬레이션에서 쓰는 변수를 종류별로 모은 문서. 시뮬레이터 값은 `config_isl.py`, 강화학습 값은 `rl/config_rl.py`에서 바꿈.
형식: 변수 설명 | 코드 이름 | 값

## 1. 위성망 (Topology)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 망 구조 | `P.topology` (환경 변수 `ISL_TOPOLOGY`) | `grid` (6x6), `grid:8x8`, `iridium`, `starlink`, `starlink:12x12` |
| 궤도면 수 | `P.numPlanes` | 6 |
| 궤도면당 위성 수 | `P.satsPerPlane` | 6 |
| 시뮬레이션 단위 시간 | `P.stepTime` | 1 ms (= 1 step) |
| 궤도 내 링크 거리 (6x6) | (코드 없음) | 1,970 km → 상/하 지연 7 step의 근거 |
| 궤도 간 링크 거리 (6x6) | (코드 없음) | 500 km → 좌/우 지연 2 step의 근거 |

- 격자가 아닌 구조(Iridium, Starlink)는 크기, 원형 연결, 링크 지연(실제 거리 ÷ 빛의 속도)을 구조에 맞게 덮어씀 (`sim/topology.py`)
- 어떤 구조든 흐름 0 끝점, 가장 먼 거리 D, 기한과 TTL 상한은 config 끝에서 그 크기에 맞춰 자동 계산 (`update_limits`)

## 2. 위성 노드

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 위성 좌표 | `(p, s)` | (0,0) ~ (궤도면 수-1, 위성 수-1), 6x6은 (5,5)까지 |
| 링크별 최대 큐 용량 | `P.queueMax` | 200 packets |
| 현재 큐 길이 | `queueLen` | 0 ~ 200 |
| 처리 지연 | `P.processingDelay` | 0 step |

## 3. 링크

| 변수 | 코드 | 값 |
| --- | --- | --- |
| ISL 대역폭 | `P.linkCapacity` | 5 packets/step |
| 같은 궤도면 지연 (상/하) | `P.linkDelay[0:2]` | 7 step |
| 옆 궤도면 지연 (좌/우) | `P.linkDelay[2:4]` | 2 step |
| 방향 번호 | `nextDir` | 1 상, 2 하, 3 좌, 4 우 |

## 4. 패킷

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 패킷 번호 | `packet_id` | 0부터 |
| 패킷 크기 | `P.packetSize` | 160 Byte |
| 초당 생성 수 (흐름마다) | `P.genRate` | 60 |
| 기한 여유 | `P.deadlineMargin` | 25 step (흐름 기한 = 그 흐름의 최소 지연 + 25) |
| TTL 여유 | `P.ttlMargin` | 10 (흐름 TTL = 그 흐름의 최소 홉 + 10) |
| 흐름별 기한, TTL (자동) | `P.mainDeadlines`, `P.mainTtls` | 에피소드마다 흐름별로 계산 (6x6 (0,0) → (5,5): 70, 20) |
| 가장 먼 흐름 0 기한, TTL (자동) | `P.deadline`, `P.ttlInit` | 6x6: 70 step, 20 (관측 정규화, 홉 보상 기준) |
| 현재 위성, 홉 수, 생성 시각 | `curP`, `curS`, `hops`, `genTime` | |

## 4-1. 주 흐름 (`sim/flows.py`)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 주 흐름 수 | `P.numFlows` | 4 |
| 흐름 0 도착 (끝점, 자동) | `P.dstSat` | 격자 맨 끝 모서리 (궤도면 수-1, 위성 수-1). 6x6 (5,5), Starlink 72x22 (71,21) |
| 흐름 0 출발 | (에피소드 시드로 무작위) | 끝점까지 길이 있는 아무 위성. 학습, 검증, 평가 모두 같은 규칙 |
| 가장 먼 거리 D (자동) | `P.maxFlowDelay` | 끝점까지 가장 먼 위성의 최소 지연. 6x6 45 step |
| 흐름 1, 2, 3 거리 구간 | `P.flowDistBands` | D의 0~1/3, 1/3~2/3, 2/3~1 (6x6: 0~15, 15~30, 30~45 step) |
| 이번 에피소드 흐름 (자동) | `P.mainFlows` | [(출발, 도착), ...] |

- 흐름끼리 출발 위성, 도착 위성이 겹치지 않게 뽑음. 흐름이 구간 수보다 많으면 구간을 처음부터 다시 씀

## 5. 라우팅

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 비교할 라우팅 | `P.routeName` | `['routeA', 'routeB']` (`routeC`는 모델 필요) |
| 데이터 수집용 라우팅 (ε > 0) | `P.collectRoute` | `'routeB'` |
| B 혼잡 임계값 | `P.draThreshold` | 0.5 (송신 큐 ≥ 100이면 혼잡) |
| 링크 점유율 가중치 (기록용) | `P.k` | 0.5 |

- **route_A:** 링크 지연 합이 최소인 경로 (Dijkstra, 큐는 보지 않음). 동점이면 좌/우 먼저
- **route_B (DRA, Ekici et al. 2001):** 주 방향(목적지 쪽 좌/우)이 혼잡하지 않으면 주, 혼잡하고 보조(목적지 쪽 상/하)가 여유 있으면 보조, 둘 다 혼잡하면 주
- **route_C:** 강화학습 (아래 11번)
- 선택 유형 `choiceType`: 1 주, 2 보조, 3 그 외, 4 무작위
- 기록용 상태: 링크 점유율 L = (k x V + (1 − k) x N) / Q, V = 보내려는 링크의 큐 길이, N = 다음 위성 링크 큐 평균, Q = 200

## 6. 배경 트래픽 (공통)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 사용 여부 | `P.bgEnable` | True |
| 방식 | `P.bgMode` | `'event'` (새 방식, 기본), `'hotspot'` (기존 방식) |
| 혼잡 단계 | `P.bgLevel` | `'base'`, `'high'`, `'severe'` |
| 시작 시드 | `P.bgScenarioSeed` | 1 (에피소드 e는 시드 + e) |
| 주 흐름 지역 가중치 | `P.bgRelWeight` | 3.0 (주 흐름 4개의 출발 → 도착 직선 근처) |
| 막힘 기준 (기존 방식) | `P.bgBlockLoad` | 1.8 |
| 배경 TTL, 동시 배경 패킷 최대 수 | `P.bgTtl`, `P.bgPoolSize` | 20, 20000 |
| 자동으로 채워지는 값 | `P.bgFlows`, `P.bgOnRate`, `P.bgSeed`, `P.bgEvents` | |
| 배경 경로 | XY 경로 (목적지 쪽 좌/우 먼저, 부하를 보지 않음) | |

### 6-1. 새 방식: 기본 부하 + 지역 핫스팟 (`sim/bg_event.py`)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 기본 부하 | `P.bgBaseMin`, `P.bgBaseMax` | 모든 링크에 용량의 0.1 ~ 0.4배 |
| 핫스팟 세기 | `P.evLoadMin`, `P.evLoadMax` | 중심 위성 송신 링크에 +0.5 ~ 1.5배 |
| 이웃 위성 비율 | `P.evNbrRatio` | 0.5 (이웃 위성 송신 링크에는 세기의 절반) |
| 주 흐름 지역 | `P.evCorridor` | 1.0 (출발 → 도착 대각선 1칸 이내 위성이 3배 더 자주) |
| 안전장치 | `P.evSafeLoad` | 1.0 (용량을 넘는 링크를 모두 빼고도 길이 있어야 함) |
| 발생 간격 평균 | `P.evIntervalMean` (`EVENT_LEVELS`), `P.evRefSats` | base 1000, high 500, severe 250 step (6x6 기준). 실제 간격 = 이 값 x 36 ÷ 위성 수 (이리듐은 1.8배 자주) |
| 지속 시간 평균 | `P.evDurationMean` (`EVENT_LEVELS`) | 1000 step (세 단계 같음) |

### 6-2. 기존 방식: 고정 핫스팟 (`sim/bg_traffic.py`, 지금은 안 씀. 웹에서는 뺌)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 핫스팟 개수 | `P.bgNumMin` ~ `P.bgNumMax` (`BG_LEVELS`) | base 2~5, high 3~6, severe 4~7 |
| 핫스팟 세기 | `P.bgLoadMin` ~ `P.bgLoadMax` | 링크 용량의 0.7 ~ 2.0배 |
| 켜짐 / 꺼짐 평균 | `P.bgOnMean`, `P.bgOffMean` (`BG_LEVELS`) | base 150/750, high 300/600, severe 450/450 step |
| 관련 큐 최소 개수 | `P.bgMinRelevant` | 1 |

## 7. 실험 설정

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 에피소드 길이 | `P.simTime` | 10000 step (10초) |
| 에피소드 개수 (= 평가 시드 1~20) | `P.numEpisodes` | 20 |
| 남은 패킷 처리 한도 | `P.maxDrainTime` | 500 step |
| 무작위 선택 확률 (main_isl) | `P.epsilonList` | 0 (성능 측정), 0.1 (데이터 수집) |
| 무작위 선택 시드 | `P.randomSeed` | 1 (에피소드 e는 randomSeed + e) |
| 애니메이션 길이, 간격 | `P.animDuration`, `P.animFrameInterval` | 200 step, 2 step |
| 노드 기록 | `P.nodeLogEnable`, `P.nodeLogInterval` | True, 100 step |
| 결과 저장 경로 | 환경 변수 `ISL_SAVE_ROOT` | 기본: 홈 폴더 `isl_saved_runs` |

## 8. 손실 / 결과 (패킷 기록 result)

| 결과 | 번호 |
| --- | --- |
| 기한 내 도착 | 1 |
| 목적지 기한 초과 | 2 |
| 중간 기한 초과 | 3 |
| 큐 오버플로 | 4 |
| TTL 만료 | 5 |

## 9. 성능 지표

| 지표 | 코드 |
| --- | --- |
| 평균 지연 (목적지 도착 패킷) | `avgLatency_ms` |
| 손실률, 기한 내 도착률 | `lossRate`, `onTimeRate` |
| 처리량 | `throughput_Mbps` |
| 최대 연속 손실 | `maxConsecLoss` |
| 경로 변경 수, 평균 홉 수 | `routeChanges`, `avgHops` |

### 9-1. 연속 손실

| 지표 | 코드 |
| --- | --- |
| 연속 손실 기준 | `P.burstMinLen` = 3 (같은 흐름 안에서 패킷 번호 순서로 3개 이상 이어진 손실, 흐름, 에피소드 경계에서 끊음) |
| 연속 손실 횟수 | `burstCount` |
| 연속 손실에 속한 패킷 수, 비율, 손실 중 비중 | `burstLossPackets`, `burstLossRate`, `burstShareOfLoss` |
| 연속 손실 평균 길이 | `avgBurstLen` |
| 1분당 연속 손실 횟수 | `burstPerMin` |
| 연속 손실 길이 95번째 백분위 | `burstLenP95` (평가와 검증) |

## 10. 기록 파일 열
- 결정 기록(`decision_log`), 노드 기록(`node_log`), 패킷 기록(`packet_log`), 연속 손실 기록(`burst_log`), 학습 기록(`train_log`, `eval_log`), 평가 기록(`summary`, `per_seed`)의 열은 저장소 최상위 `csv.md` 참고

## 11. 강화학습 (`rl/config_rl.py`)

| 변수 | 코드 | 값 |
| --- | --- | --- |
| 관측 수, 행동 수 | `RL.obsDim`, `RL.numActions` | 19 (`RL.stateMode = 'coarseIn'`: coarse 15 + 들어온 방향 4), 4 |
| 관측 정규화 | `RL.normDist`, `RL.normDeadline` | 남은 거리 ÷ 5칸 (-1~1로 자름, 망 크기와 상관없이 1칸 = 0.2, 11/23), 남은 기한 ÷ `P.deadline` (6x6: 70) |
| 행동 마스크 | `RL.maskMode` | `'noBack'` (없는 방향 + 들어온 링크를 막음). 그 밖에 `'link'`, `'deadline'` |
| 보상 | `RL.rewardOnTime`, `RL.rewardSingleLoss` | 기한 내 도착 +0.5, 단발 손실 −0.1 |
| 연속 손실 보상 | `RL.burstBase`, `RL.burstStep`, `RL.burstMax` | 패킷당 −0.3 고정 (`burstStep` 0, 5차), 시작 벌점 `RL.burstStartPenalty` 2.0 |
| 연속 손실 시작 벌점 | `RL.burstStartPenalty` | 3번째 패킷에 −0.5 한 번 더 |
| 홉 보상 | `RL.rewardHopScale`, `RL.rewardHopQueue` | −링크 지연 ÷ 70 (큐 항목 없음, `rewardHopQueue = False`) |
| 신경망 | `RL.hidden` | 19 → 64 → 64 → 4 |
| 학습률, 할인율 | `RL.lr`, `RL.gamma` | 0.0001, 0.95 |
| 리플레이 버퍼, 배치 | `RL.bufferSize`, `RL.batchSize` | 100만, 64 |
| 학습 시작, 학습 빈도 | `RL.learnStart`, `RL.trainEvery` | 경험 20만 개 이후, 결정 16번마다 (흐름 수에 비례, 흐름 하나당 5만, 4번) |
| 타깃 갱신 | `RL.targetUpdate`, `RL.tau` | 학습 2,500번마다 통째로 복사 (τ 0) |
| ε | `RL.epsStart`, `RL.epsEnd`, `RL.epsDecaySteps` | 1.0 → 0.05, 결정 40만 번 (흐름 하나당 10만) |
| 학습 에피소드, 시드 | `RL.trainEpisodes`, `RL.trainSeedStart` | 80, 1001부터 |
| 학습 혼잡 단계 | `RL.trainLevelWeights` | high : severe = 1 : 2 (비율대로 무작위, `apply_level_ratio`로 바꿈) |
| 학습 시드 (신경망 초기값) | `RL.torchSeed` | 0 (실행 인자로 바꿈) |
| 검증 평가 | `RL.evalEvery`, `RL.valSeeds`, `RL.valLevels` | 5 에피소드마다, 501~503, high, severe |
| 저장 | `RL.modelDir`, `RL.saveEvery` | 홈 폴더 `rl_models`, 10 에피소드마다 |
