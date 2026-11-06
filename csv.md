# 결과 CSV 설명

결과 파일은 실행 종류에 따라 세 곳에 생김. 모든 지표는 **주 흐름 패킷**만으로 계산하고, 배경 트래픽 패킷은 개수만 따로 기록.

| 실행 | 저장 위치 | 파일 |
| --- | --- | --- |
| ① A, B 시뮬레이션 (`main_isl.py`) | `isl_routing/results/` + `~/isl_saved_runs/라우팅_혼잡단계_날짜/` | `metrics_summary.csv`, `packet_log_*.csv`, `burst_log_*.csv`, `decision_log_*.csv`, `node_log_*.csv`, `bg_scenario.csv` |
| ② C 학습 (`rl/train_rl.py`) | `~/rl_models/routeC_날짜_s학습시드/` | `train_log.csv`, `eval_log.csv` |
| ③ 최종 평가 (`eval_routes.py`, `analysis/compare_runs.py`) | `~/isl_saved_runs/eval_날짜/` | `summary.csv`, `per_seed.csv`, `targets_report.csv` |

- ①의 파일 이름 `*` = `라우팅_rate60pps_eps값` (예: `packet_log_routeB_rate60pps_eps0.0.csv`)
- ①은 에피소드 여러 개를 이어 붙인 결과라서, 시각(`step`)과 패킷 번호가 에피소드를 지나며 계속 이어짐 (에피소드 e의 시각은 e x 에피소드 길이를 더한 값)
- 결과 번호 `result`: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료
- 방향 번호: 1 상, 2 하, 3 좌, 4 우. 없는 방향(격자 끝)은 `-1`

---

## ① A, B 시뮬레이션

### `metrics_summary.csv` : 최종 성능 지표
- **1줄 =** 실행 1번 (기본: A ε 0, B ε 0, B ε 0.1 세 줄)

| 열 | 뜻 |
| --- | --- |
| `routeName`, `genRate`, `epsilon` | 라우팅, 초당 생성 패킷 수, 무작위 선택 확률 |
| `generated`, `onTime` | 생성 수, 기한 내 도착 수 |
| `lateAtDst`, `lateMid`, `overflow`, `ttlExpired` | 손실 원인별 개수 |
| `avgLatency_ms` | 평균 지연 (목적지에 도착한 패킷, 기한 초과 도착 포함) |
| `lossRate`, `onTimeRate` | 손실률, 기한 내 도착률 |
| `throughput_Mbps` | 처리량 |
| `maxConsecLoss` | 최대 연속 손실 (에피소드 경계에서 끊음) |
| `burstMinLen`, `burstCount` | 연속 손실 기준 (3개), 연속 손실 횟수 |
| `burstLossPackets`, `burstLossRate`, `burstShareOfLoss` | 연속 손실에 속한 패킷 수, 생성 대비 비율, 전체 손실 중 비중 |
| `avgBurstLen`, `burstPerMin` | 연속 손실 평균 길이, 1분당 연속 손실 횟수 |
| `routeChanges`, `avgHops` | 경로 변경 수, 평균 홉 수 |
| `bgGenerated`, `bgDelivered`, `bgOverflow`, `bgTtlExpired`, `bgSrcDrop` | 배경 패킷 개수 (생성, 도착, 오버플로, TTL 만료, 동시 배경 패킷 한도 때문에 못 만듦) |

### `packet_log_*.csv` : 패킷별 결과
- **1줄 =** 패킷 1개

| 열 | 뜻 |
| --- | --- |
| `packet_id` | 패킷 번호 (0부터) |
| `gen_step`, `end_step` | 생성 시각, 끝난 시각 (step = ms) |
| `result` | 결과 번호 (위 참고) |
| `hops` | 거쳐 간 위성 수 |
| `episode` | 에피소드 번호 |
| `loss_run_len` | 이 패킷이 속한 손실 구간 길이 (손실 아니면 0) |
| `burst_id` | 연속 손실 번호 (`burst_log`와 연결, 연속 손실이 아니면 −1) |
| `flow_id` | 주 흐름 번호 (0 = 기존 (0,0) → (5,5) 흐름, 1 이상 = 무작위 흐름, `ISL_NUM_FLOWS`로 흐름 수 설정). 연속 손실은 흐름마다 따로 셈 |

### `burst_log_*.csv` : 연속 손실 기록
- **1줄 =** 연속 손실 1번

| 열 | 뜻 |
| --- | --- |
| `burst_id`, `episode` | 연속 손실 번호, 에피소드 |
| `first_packet_id`, `last_packet_id`, `length` | 처음과 마지막 패킷 번호, 길이 |
| `first_gen_step`, `last_gen_step`, `span_ms` | 처음과 마지막 패킷 생성 시각, 끊긴 시간 |
| `n_late_dst`, `n_late_mid`, `n_overflow`, `n_ttl` | 손실 원인별 개수 |
| `main_cause` | 가장 많은 원인 |

### `decision_log_*.csv` : 라우팅 결정 기록
- **1줄 =** 라우팅 결정 1번 (ε 0.1 실행에서만 저장)

| 구분 | 열 | 뜻 |
| --- | --- | --- |
| 식별 | `step`, `packet_id`, `hop` | 결정 시각, 패킷 번호, 몇 번째 결정인지 |
| 상태 | `cur_p`, `cur_s` | 지금 있는 위성 |
| 상태 | `q_up` ~ `q_right` | 4방향 링크 큐 길이 (배경 포함) |
| 상태 | `L_up` ~ `L_right` | 링크 점유율 L = (k x 큐 + (1 − k) x N) / 200 (기록용) |
| 상태 | `N_up` ~ `N_right` | 이웃 위성 부하 (다음 위성 링크 큐 평균) |
| 상태 | `rem_dp`, `rem_ds`, `rem_deadline`, `ttl` | 남은 거리, 남은 기한, 남은 TTL |
| 행동 | `action`, `choice_type` | 고른 방향, 선택 유형 (1 주, 2 보조, 3 그 외, 4 무작위) |
| 결과 | `enqueued` | 1 큐에 들어감, 0 오버플로 |

※ C의 학습은 이 파일을 쓰지 않고 시뮬레이터 안에서 바로 경험을 모음 (`rl/rl_collector.py`)

### `node_log_*.csv` : 노드 기준 기록
- **1줄 =** 기록 시각 1번 x 노드 1개 (`P.nodeLogInterval` = 100 step마다)

| 열 | 뜻 |
| --- | --- |
| `step`, `p`, `s` | 기록 시각, 노드 좌표 |
| `q_up` ~ `q_right`, `qmax_up` ~ `qmax_right` | 링크별 큐 길이, 직전 기록 이후 최대 큐 길이 |
| `main_queued`, `bg_queued` | 큐 안 주 흐름, 배경 패킷 수 |
| `min_rem_deadline` | 큐 안 주 흐름 패킷의 남은 기한 최솟값 (−1: 없음) |
| `main_sent`, `bg_sent`, `main_overflow`, `bg_overflow` | 직전 기록 이후 보낸 수, 오버플로 수 |
| `main_late_mid`, `main_ttl_expired`, `main_on_time`, `main_late_dst` | 직전 기록 이후 이 노드에서 끝난 주 흐름 수 |

### `bg_scenario.csv` : 에피소드별 배경 트래픽
- **1줄 =** 배경 흐름 1개 (새 방식은 기본 부하 링크와 핫스팟 링크 모두)

| 열 | 뜻 |
| --- | --- |
| `episode`, `seed` | 에피소드, 그 에피소드의 시드 |
| `p`, `s`, `direction` | 배경 흐름의 출발 위성과 방향 |
| `load` | 세기 (링크 용량의 몇 배) |
| `hotspot` (새 방식) / `relevant` (기존 방식) | 1 지역 핫스팟 링크, 0 기본 부하 / 1 주 흐름 관련 큐 |
| `start`, `end` (새 방식만) | 켜져 있는 구간 (step) |

---

## ② C 학습

### `train_log.csv` : 학습 중 기록 (ε 포함)
- **1줄 =** 학습 에피소드 1개

| 열 | 뜻 |
| --- | --- |
| `episode`, `level`, `seed` | 에피소드 번호, 혼잡 단계, 시드 |
| `onTimeRate`, `lossRate` | 기한 내 도착률, 손실률 (%, 무작위 탐험 포함) |
| `burstCount`, `burstPackets`, `burstPacketRate`, `maxConsecLoss` | 연속 손실 횟수, 속한 패킷 수와 비율, 최대 연속 손실 |
| `epsilon`, `decisions` | ε, 누적 결정 수 |
| `burstPenalties` | 연속 손실 보상을 받은 패킷 수 |
| `rewardHopSum`, `rewardOutcomeSum`, `rewardBurstSum` | 보상 성분별 합 (홉, 도착과 단발 손실, 연속 손실) |
| `infeasibleMasks` | 마스크 예외 횟수 (`maskMode = 'full'`일 때만 의미 있음) |
| `meanLoss` | 학습 손실 평균 (Huber) |
| `transitions`, `unfinished`, `bufferSize` | 만든 경험 수, 끝나지 않은 패킷 수, 버퍼 크기 |
| `seconds` | 걸린 시간 |

### `eval_log.csv` : 검증 평가 (학습 곡선용, ε 0)
- **1줄 =** 검증 1번 x 혼잡 단계 1개 (학습 전 1번, 그 뒤 10 에피소드마다)
- 검증 시드 501~505 에피소드를 합친 값. 학습 곡선과 목표 판정(`analysis/learning_targets.py`)은 이 파일을 씀

| 열 | 뜻 |
| --- | --- |
| `evalIndex`, `episode` | 검증 번호 (0 = 학습 전), 그때까지 학습한 에피소드 수 |
| `decisions`, `epsilon` | 누적 결정 수 (곡선의 가로축), 그때의 ε |
| `level` | 혼잡 단계 |
| `onTimeRate` | 기한 내 도착률 (%) |
| `burstCount`, `burstPerMin` | 연속 손실 횟수, 1분당 연속 손실 횟수 |
| `burstLenP95`, `maxConsecLoss` | 연속 손실 길이 95번째 백분위, 최대 연속 손실 |
| `avgLatency_ms` | 평균 지연 |
| `meanLoss` | 직전 검증 이후 에피소드들의 학습 손실 평균 |
| `seconds` | 검증에 걸린 시간 |

---

## ③ 최종 평가와 목표 판정

### `summary.csv` : 단계 x 라우팅(x C 모델)별 합계
- **1줄 =** 혼잡 단계 1개 x 라우팅 1개 (C는 모델마다 한 줄, `cRun` = 모델 순번)
- `metrics_summary.csv`의 주요 지표에 아래가 더해짐

| 열 | 뜻 |
| --- | --- |
| `level`, `route`, `cRun` | 혼잡 단계, 라우팅, C 모델 순번 (A, B는 빈칸) |
| `lossRuns`, `runs_ge5`, `runs_ge10` | 손실 구간 수, 5개 이상, 10개 이상 이어진 손실 횟수 |
| `worstEpisodeOnTime` | 가장 나쁜 평가 에피소드의 도착률 |
| `burstPerMin`, `burstLenP95` | 1분당 연속 손실 횟수, 연속 손실 길이 95번째 백분위 |

### `per_seed.csv` : 평가 시드별 결과
- **1줄 =** 혼잡 단계 x 라우팅(x C 모델) x 평가 시드 1개
- 짝지은 승률(같은 시드에서 C가 B보다 연속 손실이 적은 비율)과 최악 에피소드 비교에 씀

| 열 | 뜻 |
| --- | --- |
| `level`, `route`, `cRun`, `seed` | 혼잡 단계, 라우팅, C 모델 순번, 평가 시드 |
| `onTimeRate`, `burstCount`, `burstPerMin`, `burstLenP95`, `maxConsecLoss`, `avgLatency_ms` | 그 에피소드의 지표 |

### `targets_report.csv` : C 모델별 목표 판정 값 (`analysis/compare_runs.py`)
- **1줄 =** 혼잡 단계 x C 모델 1개. 판정표는 같은 폴더의 `targets_report.md`

| 열 | 뜻 |
| --- | --- |
| `burstCut`, `p95Cut` | B 대비 1분당 연속 손실 감소율, 95번째 백분위 길이 감소율 (%) |
| `onTimeDiff`, `latencyDiff` | B 대비 도착률 차이 (%p), 지연 차이 (ms) |
| `winRate`, `ties`, `n` | 짝지은 승률 (%), 같은 수, 평가 시드 수 |
| `worstOk`, `worstC`, `worstB` | 최악 에피소드 도착률 비교 결과와 값 |
| `cLoss`, `cOnTime` | C의 손실률, 도착률 |
