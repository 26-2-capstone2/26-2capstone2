# 시뮬레이션 결과 CSV 설명

시뮬레이션(`main_isl`)을 실행하면 `results/` 폴더에 CSV 3종류가 생성됨.
**요약 → 패킷 단위 → 결정 단위** 순서
MATLAB(`ISL-MATLAB`)과 Python(`ISL-Python`) 버전 모두 같은 파일이 나오고, 값도 동일.

| 파일 | 1줄 = | 용도 |
| --- | --- | --- |
| `metrics_summary.csv` | 실행 1번 | 최종 성능 지표 (보고서, 비교용) |
| `packet_log_*.csv` | 패킷 1개 | 패킷별 생성, 종료 시각과 결과 |
| `decision_log_*.csv` | 라우팅 결정 1번 | 강화학습 학습 데이터 |

---

## 1. `metrics_summary.csv` : 최종 성능 지표

- **용도**: 실행마다 성능 지표를 한 줄로 요약. 보고서/발표용 숫자이자, 나중에 강화학습과 비교할 기준
- **1줄 =** 실행 1번 (현재 ε = 0, ε = 0.1 두 줄)

| 열 | 뜻 |
| --- | --- |
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

| 구분 | 열 | 뜻 |
| --- | --- | --- |
| 식별 | `step` | 결정한 시각 (ms) |
| 식별 | `packet_id` | 패킷 번호 |
| 식별 | `hop` | 몇 번째 결정인지 (지금까지 거친 홉 수) |
| 상태 | `cur_p`, `cur_s` | 지금 있는 위성 좌표 |
| 상태 | `q_up`, `q_down`, `q_left`, `q_right` | 상/하/좌/우 링크 큐 길이 |
| 상태 | `L_up`, `L_down`, `L_left`, `L_right` | 상/하/좌/우 링크 점유율 L |
| 상태 | `N_up`, `N_down`, `N_left`, `N_right` | 상/하/좌/우 이웃 위성 부하 N |
| 상태 | `rem_dp`, `rem_ds` | 목적지까지 남은 거리 (도착 p − 현재 p, 도착 s − 현재 s) |
| 상태 | `rem_deadline` | 남은 기한 = 100 − (현재 step − 생성 step) |
| 상태 | `ttl` | 남은 TTL |
| 행동 | `action` | 고른 방향 (1 상, 2 하, 3 좌, 4 우) |
| 행동 | `choice_type` | 1 주 경로, 2 대체 경로, 3 우회, 4 무작위 |
| 결과 | `enqueued` | 1 큐에 들어감, 0 오버플로로 버려짐 |

※ Grid 끝이라 없는 방향은 `-1`

---

## packet_log + decision_log 함께 쓰기 (강화학습 보상 계산)

결정 기록에는 "이 선택이 결국 좋았는지"가 없으므로, 강화학습 단계에서 `packet_id`로 두 파일을 연결.

1. `decision_log`에서 이 상황(상태)에서 이 방향(행동)을 골랐는지를 가져옴
2. `packet_log`에서 그 패킷이 **결국 기한 안에 도착했는지(`result`), 언제 끝났는지(`end_step`)를 가져옴
3. 둘을 합쳐 보상(Reward) 계산

보상을 기록에 미리 넣지 않은 이유: 보상 식을 바꿔도 시뮬레이션을 다시 돌릴 필요 없이 두 파일만 다시 연결하면 됨
