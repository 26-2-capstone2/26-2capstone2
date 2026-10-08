# 시뮬레이션 결과 CSV 설명

시뮬레이션(`main_isl`)을 실행하면 `results/` 폴더에 CSV 4종류가 생성됨.
**요약 → 패킷 단위 → 결정 단위 → 노드 단위** 순서.
여러 시드 실험(`run_experiments`)은 요약 CSV 2종류를 추가로 만듦 (5번).

| 파일 | 1줄 = | 용도 |
| --- | --- | --- |
| `metrics_summary.csv` | 실행 1번 | 최종 성능 지표 (보고서, 비교용) |
| `packet_log_*.csv` | 패킷 1개 | 패킷별 생성, 종료 시각과 결과 |
| `decision_log_*.csv` | 라우팅 결정 1번 | 강화학습 학습 데이터 |
| `node_log_*.csv` | 기록 시각 1번 x 노드 1개 | 노드 기준 상태 (큐, 보낸 수, 손실) |
| `eval_runs.csv`, `eval_stats.csv` | 실행 1번 / 단계 x 지표 | 여러 시드 실험 요약 (평균 ± 편차) |

모든 지표는 **주 흐름 패킷**만으로 계산함. 배경 트래픽 패킷은 개수만 따로 기록.

---

## 1. `metrics_summary.csv` : 최종 성능 지표

- **용도**: 실행마다 성능 지표를 한 줄로 요약. 보고서/발표용 숫자이자, 나중에 강화학습과 비교할 기준
- **1줄 =** 실행 1번 (`main_isl`은 ε = 0, ε = 0.1 두 줄)

| 열 | 뜻 |
| --- | --- |
| `routeName` | 라우팅 알고리즘 (`routeA` 최단 경로, `routeB` 부하 고려) |
| `genRate`, `epsilon` | 실행 조건 (1초마다 생성 패킷 수, 무작위 선택 확률) |
| `generated` | 생성한 패킷 수 |
| `onTime` | 기한 내 도착한 패킷 수 |
| `lateAtDst`, `lateMid`, `overflow`, `ttlExpired` | 손실 원인별 개수 (목적지 기한 초과, 중간 기한 초과, 큐 오버플로, TTL 만료) |
| `avgLatency_ms` | Average Latency (ms) |
| `lossRate` | Packet Loss Rate |
| `throughput_Mbps` | Throughput (Mbps) |
| `onTimeRate` | On-time Delivery Rate |
| `maxConsecLoss` | Consecutive Packet Loss Length |
| `routeChanges` | Route Change Count |
| `avgHops` | Average Hop Count |
| `bgGenerated`, `bgDelivered`, `bgOverflow`, `bgTtlExpired`, `bgPoolFull` | 배경 트래픽 개수 (생성, 도착, 큐 오버플로, TTL 만료, 자리가 없어 생성 못 함) |

---

## 2. `packet_log_*.csv` : 패킷별 결과

- **용도**: 패킷 하나하나가 언제 생겨서 어떻게 끝났는지 기록. 성능 지표 7개를 모두 이 파일로 계산할 수 있고, 지연 분포·시간대별 변화 분석에 사용
- **1줄 =** 패킷 1개 (10분 실행이면 36,000줄)
- 파일 이름: `packet_log_rate60pps_eps0.0.csv` (성능 측정용), `packet_log_rate60pps_eps0.1.csv` (데이터 수집용)

| 열 | 뜻 |
| --- | --- |
| `packet_id` | 패킷 번호 (0부터) |
| `gen_step` | 생성된 시각 (step = ms) |
| `end_step` | 도착했거나 버려진 시각 (step = ms) |
| `result` | 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료 |
| `hops` | 거쳐 간 위성 수 |

예) `0,1,46,1,10` → 0번 패킷이 1 ms에 생성되어 46 ms에 기한 내 도착, 10홉 거침

---

## 3. `decision_log_*.csv` : 라우팅 결정 기록 (강화학습 데이터)

- **용도**: 위성이 "어느 방향으로 보낼지" 정할 때마다 그때의 상황과 선택을 기록. 나중에 강화학습을 학습시키는 데이터
- **1줄 =** 라우팅 결정 1번 (약 40만 줄)
- 데이터 수집용(ε = 0.1) 실행에서만 저장: `decision_log_rate60pps_eps0.1.csv`
  (`run_experiments`의 학습 데이터 수집 `B.runTrain`에서도 실행마다 저장)
- 패킷 기준 기록: 패킷이 위성을 지날 때만 남음. `packet_id`로 모으면 그 패킷의 경로가 됨

| 구분 | 열 | 뜻 |
| --- | --- | --- |
| 식별 | `step` | 결정한 시각 (ms) |
| 식별 | `packet_id` | 패킷 번호 |
| 식별 | `hop` | 몇 번째 결정인지 (지금까지 거친 홉 수) |
| 상태 | `cur_p`, `cur_s` | 지금 있는 위성 좌표 |
| 상태 | `q_up`, `q_down`, `q_left`, `q_right` | 상/하/좌/우 링크 큐 길이 (배경 패킷 포함) |
| 상태 | `L_up`, `L_down`, `L_left`, `L_right` | 상/하/좌/우 링크 점유율 L = (k·큐 + (1−k)·N) / 200 |
| 상태 | `N_up`, `N_down`, `N_left`, `N_right` | 상/하/좌/우 이웃 위성 부하 N (다음 위성 링크 큐 평균) |
| 상태 | `rem_dp`, `rem_ds` | 목적지까지 남은 거리 (도착 p − 현재 p, 도착 s − 현재 s) |
| 상태 | `rem_deadline` | 남은 기한 = 90 − (현재 step − 생성 step) |
| 상태 | `ttl` | 남은 TTL |
| 행동 | `action` | 고른 방향 (1 상, 2 하, 3 좌, 4 우) |
| 행동 | `choice_type` | 1 주 경로, 2 대체 경로, 3 우회, 4 무작위 (라우팅이 고른 방향을 뺀 나머지 중 하나) |
| 결과 | `enqueued` | 1 큐에 들어감, 0 오버플로로 버려짐 |

※ Grid 끝이라 없는 방향은 `-1`
※ route_A는 L, N을 결정에 쓰지 않음 (기록용). `choice_type`은 1 또는 4만 나옴

---

## 4. `node_log_*.csv` : 노드 기준 기록

- **용도**: 노드(위성)마다 큐가 얼마나 찼는지, 무엇을 보내고 어디서 손실이 났는지를 시간에 따라 기록. 혼잡한 노드 찾기, 노드별 분석
- **1줄 =** 기록 시각 1번 x 노드 1개 (`P.nodeLogInterval` = 100 step마다 36줄, 10분이면 약 21만 줄)
- 보기: `show_results.py` (요약 지도 + 손실이 가장 많은 노드), `show_node.py p s` (원하는 노드)

| 열 | 뜻 |
| --- | --- |
| `step`, `p`, `s` | 기록 시각, 노드 좌표 |
| `q_up` ~ `q_right` | 기록 시각의 링크별 큐 길이 (그 step 전송 후 남은 것) |
| `qmax_up` ~ `qmax_right` | 직전 기록 이후 링크별 최대 큐 길이 (전송 직전 기준) |
| `main_queued`, `bg_queued` | 기록 시각에 이 노드 큐에 있는 주 흐름 / 배경 패킷 수 |
| `min_rem_deadline` | 이 노드 큐 안 주 흐름 패킷의 남은 기한 최솟값 (−1: 주 흐름 패킷 없음) |
| `main_sent`, `bg_sent` | 직전 기록 이후 이 노드가 보낸 패킷 수 |
| `main_overflow`, `bg_overflow` | 직전 기록 이후 이 노드에서 큐 오버플로로 버려진 수 |
| `main_late_mid`, `main_ttl_expired` | 직전 기록 이후 이 노드에서 중간 기한 초과 / TTL 만료된 주 흐름 수 |
| `main_on_time`, `main_late_dst` | 직전 기록 이후 이 노드(목적지)에 기한 내 / 기한 초과로 도착한 수 |

※ 없는 방향(Grid 끝)은 `-1`

---

## 5. 여러 시드 실험 요약 (`run_experiments`)

`results/experiments/evaluation/` (학습 데이터는 `train/`)과 `baseline_py\routeB\evaluation\routeB_summary_...\results\`에 저장.
실행 1개마다의 `metrics_summary.csv`, `packet_log_*.csv`는 `baseline_py\routeB\evaluation\routeB_단계_시드\results\`에 따로 저장.

**`eval_runs.csv`** (1줄 = 실행 1번)

| 열 | 뜻 |
| --- | --- |
| `mode` | `eval` (평가) / `train` (학습 데이터 수집) |
| `name` | 실행 이름 (예: `routeB_mid_102`) |
| `level`, `bgRate`, `seed` | 배경 부하 단계, 흐름별 전송률, 시드 |
| 나머지 | `metrics_summary.csv`와 같은 지표 + `late` (기한 초과 합) + `runTime_s` (실행 시간) |

**`eval_stats.csv`** (1줄 = 부하 단계 x 지표)

| 열 | 뜻 |
| --- | --- |
| `level` | 배경 부하 단계 |
| `metric`, `name`, `unit` | 지표 (기한 내 도착률, 손실률, 평균 지연, 최대 연속 손실, 오버플로, 기한 초과, 경로 변경 수, 평균 홉 수) |
| `n` | 시드 수 |
| `mean`, `std`, `min`, `max` | 평균, 표준편차, 최소, 최대 (비율은 %) |

`conditions.txt`에 그 실험의 고정 조건(기한, 용량, 큐, 배경 패턴, 시드)이 같이 기록됨.

---

## packet_log + decision_log 함께 쓰기 (강화학습 보상 계산)

결정 기록에는 "이 선택이 결국 좋았는지"가 없으므로, 강화학습 단계에서 `packet_id`로 두 파일을 연결.

1. `decision_log`에서 이 상황(상태)에서 이 방향(행동)을 골랐는지를 가져옴
2. `packet_log`에서 그 패킷이 **결국 기한 안에 도착했는지(`result`), 언제 끝났는지(`end_step`)**를 가져옴
3. 둘을 합쳐 보상(Reward) 계산

보상을 기록에 미리 넣지 않은 이유: 보상 식을 바꿔도 시뮬레이션을 다시 돌릴 필요 없이 두 파일만 다시 연결하면 됨
