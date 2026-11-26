# ISL 라우팅 시뮬레이션 사용 안내

LEO 위성 사이 링크(ISL)에서 실시간 UDP 흐름 4개(흐름 0: 무작위 위성 → 격자 맨 끝 모서리, 흐름 1~3: 짧은, 중간, 긴 경로 무작위 쌍)를 보내고, 라우팅 A(최단 경로), B(DRA), C(강화학습)가 **연속 패킷 손실을 줄이고 기한 내 도착률을 높이는지** 비교함.

## 0. 준비

```bash
pip install -r requirements.txt
```

필요한 패키지: numpy, matplotlib, Pillow, torch (torch는 C를 학습하거나 평가할 때만 필요)

## 1. 실행 방법

### 가장 쉬운 방법: `run.py`
```bash
python run.py
```
질문에 번호로 답하면 됨. 엔터만 누르면 [괄호] 안의 기본값.
1. 할 일: 시뮬레이션 / C 학습 / B, C 비교 평가 / 테스트
2. 망 구조: 6x6 격자 / 크기 지정 격자 / Iridium / Starlink / Starlink 축소판
3. 할 일에 따라: 혼잡 단계, 라우팅, 시드, 에피소드 수, 학습 시드, C 모델
4. 설정 확인 후 `Y`

### 직접 실행

| 할 일 | 명령 |
| --- | --- |
| B 시뮬레이션 (A는 라우팅 인자로) | `python main_isl.py` (인자: 시작 시드, 혼잡 단계, 라우팅, 예: `python main_isl.py 1 severe routeB`) |
| 학습된 C로 시뮬레이션 | `python main_isl.py 1 severe routeC 모델경로/model_final.pt` |
| C 학습 | `python rl/train_rl.py 80 0 0` (에피소드 수, 에피소드 길이 0 = 기본값, 학습 시드) |
| 학습 곡선 목표 판정 | `python analysis/learning_targets.py 학습폴더 [학습폴더 ...]` |
| B, C 최종 평가 (A는 routeA,routeB,routeC로 고를 때만) | `python eval_routes.py 모델0,모델1,모델2` (평가 시드 1~20 x 혼잡 3단계) |
| 최종 성능 목표 판정 | `python analysis/compare_runs.py 평가폴더` |
| 여러 세트 한 번에 | `python tools/run_batch.py high routeB 1001 5` |
| 테스트 | `python -m unittest discover -s tests` |

망 구조는 환경 변수 `ISL_TOPOLOGY`로 고름: `grid` (기본 6x6), `grid:8x8`, `iridium`, `starlink`, `starlink:12x12`
- PowerShell: `$env:ISL_TOPOLOGY="iridium"; python rl/train_rl.py`
- bash: `ISL_TOPOLOGY=iridium python rl/train_rl.py`
- 어떤 구조든 흐름 0 도착(맨 끝 모서리), 흐름 1~3 거리 구간, 흐름별 기한과 TTL은 그 구조에 맞게 자동으로 계산됨

## 2. 결과 확인

### 창으로 보기
- `python tools/show_results.py`: 지표 표, 지표 그래프, 실행 분석, 노드 그림, 애니메이션
- `python tools/show_node.py 5 2`: 노드 (5,2)의 시간 변화 (인자 없으면 손실이 가장 많은 노드)

### 파일로 보기
| 파일 | 내용 |
| --- | --- |
| `metrics_summary.png` / `.csv` | 성능 지표 비교 |
| `run_analysis.png` | 지연 분포, 시간별 변화, 링크 사용량, 홉 수, 선택 유형, 손실 원인 |
| `burst_analysis.png` | 연속 손실 분석 |
| `anim_*.gif` | 첫 에피소드 처음 0.2초 애니메이션 |
| `packet_log_*.csv`, `burst_log_*.csv`, `decision_log_*.csv`, `node_log_*.csv`, `bg_scenario.csv` | 패킷, 연속 손실, 결정, 노드, 배경 트래픽 기록 |
| `train_log.csv`, `eval_log.csv`, `learning_targets.md`, `learning_curve_eval.png` | C 학습 기록, 검증 평가, 학습 곡선 판정 |
| `summary.csv`, `per_seed.csv`, `targets_report.md` | 최종 평가와 성능 목표 판정 |

열 설명은 저장소 최상위의 `csv.md` 참고.

## 3. 결과 저장 경로 (프로젝트 밖, 홈 폴더)

| 실행 | 위치 |
| --- | --- |
| 시뮬레이션 | `~/isl_saved_runs/라우팅_혼잡단계_날짜/` (`code/` 그때 코드, `results/` 결과) |
| C 학습 | `~/rl_models/routeC_날짜_s학습시드/` |
| 최종 평가 | `~/isl_saved_runs/eval_날짜/` |

- `isl_routing/results/`는 최근 시뮬레이션 결과만 있고 실행할 때마다 비워짐 (git 제외)
- 같은 날 또 실행하면 이름 뒤에 `_2`, `_3`
- 저장 위치 변경: 환경 변수 `ISL_SAVE_ROOT` (시뮬레이션, 평가), `RL_SAVE_ROOT` (학습)

## 4. 설정값 바꾸기

| 파일 | 내용 |
| --- | --- |
| `config_isl.py` | 시뮬레이터: 망, 큐, 링크, 흐름, 기한 여유, 생성률, 에피소드, 배경 트래픽, 혼잡 단계 |
| `rl/config_rl.py` | 강화학습: State 정규화, 보상, 신경망, 학습률, ε, 버퍼, 검증 평가 |

주요 값

| 변수 | 값 |
| --- | --- |
| `P.simTime`, `P.numEpisodes` | 에피소드 10초 (10,000 step), 평가 에피소드 20개 |
| `P.numFlows`, `P.genRate` | 주 흐름 4개, 흐름마다 초당 60개 |
| `P.flowDistBands` | 흐름 1, 2, 3 거리 구간 (가장 먼 거리 D의 0~1/3, 1/3~2/3, 2/3~1. 6x6은 D = 45 ms) |
| `P.deadlineMargin`, `P.ttlMargin` | 흐름마다 기한 = 최소 지연 + 25, TTL = 최소 홉 + 10 (6x6 (0,0) → (5,5)는 70, 20) |
| `P.deadline`, `P.ttlInit` | 가장 먼 흐름 0의 기한, TTL (자동 계산, 관측 정규화 기준. 6x6: 70, 20) |
| `P.bgMode` | `'event'` 새 배경 트래픽 (기본), `'hotspot'` 기존 방식 |
| `EVENT_LEVELS` | 혼잡 단계별 핫스팟 발생 간격, 지속 시간 |
| `RL.trainEpisodes`, `RL.lr`, `RL.epsDecaySteps` | 학습 80 에피소드, 학습률 0.0001, ε 감소 결정 40만 번 (흐름 하나당 10만) |

모든 변수 설명은 `docs/variables_isl.md` 참고.

## 5. 파일 역할

### 직접 실행하는 파일
| 파일 | 역할 |
| --- | --- |
| `run.py` | 터미널 실행 도우미 |
| `main_isl.py` | A, B 시뮬레이션 + 결과 저장 |
| `eval_routes.py` | B, C 최종 평가 (A는 routeA,routeB,routeC로 고를 때만) |
| `rl/train_rl.py` | C 학습 + 검증 평가 |
| `analysis/learning_targets.py` | 학습 곡선 목표 판정 |
| `analysis/compare_runs.py` | 최종 성능 목표 판정 |
| `tools/show_results.py`, `tools/show_node.py` | 결과, 노드 보기 |
| `tools/check_bg.py` | 배경 트래픽 점검 |
| `tools/run_batch.py` | 여러 세트 실행 |

### 자동으로 불리는 파일
| 폴더 | 파일 |
| --- | --- |
| `sim/` | `run_isl_sim.py` 에피소드 1개 실행, `build_grid.py` 격자, `topology.py` 망 구조와 끝점, 기한 계산, `flows.py` 주 흐름 뽑기, `bg_event.py` 새 배경 트래픽, `bg_traffic.py` 기존 배경 트래픽, `link_history.py` 링크 기록, `episodes.py` 에피소드 합치기, `node_log.py` 노드 기록 |
| `routing/` | `route_A.py` Dijkstra, `route_B.py` DRA, `route_C.py` 강화학습 |
| `rl/` | `rl_agent.py` Double DQN, `rl_state.py` State와 마스크, `rl_reward.py` 보상, `rl_collector.py` 경험 연결 |
| `analysis/` | `compute_metrics.py` 지표, `burst_loss.py` 연속 손실 구간, `burst_summary.py` 연속 손실 요약, `save_results.py` 결과 저장 |
| `viz/` | 그래프, 애니메이션, 색 (`viz_colors.py`) |

## MATLAB 버전과 다른 점
- 좌표와 패킷 번호는 0부터 (MATLAB 내부는 1부터, 기록 파일 숫자는 같음)
- 배경 트래픽, 에피소드, 혼잡 단계, 라우팅 A, 강화학습, 노드 기록은 Python 버전에만 있음
