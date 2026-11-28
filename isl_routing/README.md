# ISL 라우팅 시뮬레이션 + 강화학습

명지대학교 26-2 캡스톤디자인2

LEO 위성 사이 링크(ISL)에서 실시간 UDP 패킷을 보낼 때, **측정 흐름(흐름 0)의 연속 패킷 손실을 줄이고 기한 내 도착률을 높이는** 라우팅을 비교함.

| 라우팅 | 방식 |
|---|---|
| routeA | Dijkstra 최단 경로 (링크 지연만 봄, 기준선) |
| routeB | DRA (자기 송신 큐가 100개 이상이면 보조 방향) |
| routeC | 강화학습 (Double DQN, 위성들이 신경망 하나를 공유하는 CTDE) |

노션: https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## 설치

```
pip install -r requirements.txt
```

torch는 강화학습(routeC)을 학습, 적응, 평가할 때만 필요함.

## 실행 (이 폴더에서)

**가장 쉬운 방법: `python run.py`**
할 일(시뮬레이션, C 학습, C 적응, B와 C 비교 평가, 테스트), 격자, 혼잡 단계, 라우팅, 시드, 에피소드 수를 번호로 고름. 엔터만 누르면 기본값.

실험 순서: **C 학습** (학습 전용 격자, 기본 10x10) → (선택) **C 적응** (평가할 격자에서 5 에피소드) → **B, C 비교 평가** (평가할 격자, 시드 1~20)

| 할 일 | 명령 |
|---|---|
| 시뮬레이션 (기본 B) | `python main_isl.py` |
| 시드, 혼잡 단계, 라우팅 지정 | `python main_isl.py 1 severe routeB` |
| 학습된 C로 시뮬레이션 | `python main_isl.py 1 severe routeC 모델경로/model_final.pt` |
| C 학습 (에피소드 수, 길이 0 = 기본, 학습 시드) | `ISL_TOPOLOGY=grid:10x10 python rl/train_rl.py 80 0 0` (짧게 시험: `python rl/train_rl.py 3 2000 0`) |
| C 적응 (평가할 격자에서) | `ISL_TOPOLOGY=iridium python rl/adapt_rl.py 모델경로/model_final.pt` |
| 학습 곡선 목표 판정 | `python analysis/learning_targets.py 학습폴더 [학습폴더 ...]` |
| B, C 최종 평가 | `ISL_TOPOLOGY=iridium python eval_routes.py 모델0,모델1,모델2` (기본 high, severe, `all`이면 base 포함) |
| 최종 평가 막대 그림 | `python viz/plot_eval.py 평가폴더` |
| 최종 성능 목표 판정 | `python analysis/compare_runs.py 평가폴더` |
| 테스트별 학습 곡선 비교 | `python viz/plot_compare_tests.py "이름=학습폴더" ...` |
| 흐름별 결과 그림 | `python viz/plot_flows.py 결과폴더` (시뮬레이션 뒤 자동 실행) |
| 여러 세트 한 번에 실행 | `python tools/run_batch.py high routeB 1001 5` |
| 테스트 | `python -m unittest discover -s tests` |

- PowerShell에서는 환경 변수를 `$env:ISL_TOPOLOGY="iridium"; python ...`처럼 줌
- 학습 시드 3개를 동시에 돌리려면 터미널 3개에서 마지막 숫자만 0, 1, 2로 바꿔 실행

## 망 구조

**모두 끝이 막힌 직사각형 가상 격자** (11/26 회의: 실제 위성군의 극지방 링크 꺼짐, seam, 원형 연결은 쓰지 않고, 위성 수만 실제와 맞춤). 링크 지연 상하 7, 좌우 2 ms 고정. 환경 변수 `ISL_TOPOLOGY`로 고름 (`sim/topology.py`).

| 값 | 격자 | 위성 수 | 측정 흐름 | 측정 흐름 기한 |
|---|---|---|---|---|
| `grid` (기본) | 6 x 6 | 36 | (0,0) → (5,5) | 70 ms |
| `grid:10x10` (학습 기본) | 10 x 10 | 100 | (0,0) → (9,9) | 106 ms |
| `iridium` | 6 x 11 | 66 | (0,0) → (5,10) | 105 ms |
| `grid:20x20` | 20 x 20 | 400 | (0,0) → (19,19) | 196 ms |
| `grid:36x36` | 36 x 36 | 1,296 | (0,0) → (35,35) | 340 ms |
| `starlink` | 72 x 22 | 1,584 | (0,0) → (71,21) | 자동 계산 |

어떤 격자를 골라도 측정 흐름 끝점, 흐름별 기한과 TTL, 핫스팟 빈도가 그 크기에 맞게 자동으로 정해지고, 결과 폴더 이름에 격자 이름이 붙음 (`sim/topology.py`의 `update_limits`).

## 결과 저장 위치 (프로젝트 밖, 홈 폴더)

- 시뮬레이션 결과: `~/isl_saved_runs/라우팅_혼잡단계_날짜/`
- 학습된 모델과 학습 기록: `~/rl_models/routeC_격자_날짜_s학습시드/` (6x6은 격자 이름 없음)
- 적응한 모델: `~/rl_models/routeC_adapt_원래폴더_to_격자_날짜/`
- 최종 평가: `~/isl_saved_runs/eval_날짜/`

## 폴더 구조

```
run.py             터미널 실행 도우미
main_isl.py        시뮬레이션 실행 (결과 CSV, 그래프, 애니메이션 저장)
config_isl.py      시뮬레이터 설정값, 배경 트래픽, 혼잡 단계
eval_routes.py     B, C를 같은 조건으로 평가 (A 선택 가능, 평가 시드별 결과 포함)

routing/    라우팅 route_A, route_B, route_C (입력과 출력이 같아서 바꿔 끼움)
sim/        시뮬레이터 본체, 망 구조, 흐름(측정 흐름, 다른 GSL 흐름), 배경 트래픽(bg_event 지금 방식, bg_traffic 이전 방식),
            에피소드 합치기, 노드 기록, 링크 기록
analysis/   성능 지표, 측정 흐름 골라내기(measured), 연속 손실, 학습 곡선 목표 판정, 최종 성능 목표 판정, 결과 저장
rl/         강화학습 설정, State 15개, 보상, DQN, 경험 연결, 학습(train_rl), 적응(adapt_rl), 모델 정보, 학습 기록
viz/        그래프, 애니메이션, 흐름별 결과, 최종 평가 막대, 학습 곡선, 테스트별 학습 곡선 비교
tools/      보조 실행: run_batch (여러 세트), show_results (결과 보기), show_node (노드 보기), check_bg (배경 트래픽 점검)
docs/       사용법, 코드 흐름, CSV 설명, 시뮬레이션 설명, 변수 설명
tests/      흐름, 강화학습 계산 확인 테스트
```

## 주요 정의

- **손실:** 기한 내에 도착하지 못한 모든 패킷 (목적지 기한 초과, 중간 기한 초과, 큐 넘침, TTL 만료)
- **연속 손실:** 같은 흐름 안에서 패킷 번호 순서로 손실이 3개 이상 이어진 구간 (흐름, 에피소드 경계에서 끊음, `analysis/burst_loss.py`)
- **주 흐름:** 4개, 흐름마다 초당 60개. 에피소드 시드로 정해지고 에피소드 동안 고정 (`sim/flows.py`). 흐름끼리 출발, 도착 위성이 겹치지 않음
  - 흐름 0 = **측정 흐름** (우리 GSL에서 들어와 가장 먼 곳까지): 시험(검증, 최종 평가) 때 (0,0) → 끝 모서리 고정, 학습과 적응 때는 그 최소 지연의 90% 이상인 쌍 중 무작위. **성능 지표는 모두 이 흐름 기준**
  - 흐름 1~3 = **다른 GSL 흐름**: 가장 먼 거리의 25~100%를 세 구간으로 나눠 짧은, 중간, 먼 흐름이 고르게 섞임. RL이 함께 라우팅하지만 지표에는 안 들어감
- **기한, TTL:** 흐름마다 그 흐름 거리에 비례. 기한 = max(최소 지연 x 70/45, 최소 지연 + 25), TTL = max(최소 홉 x 2, 최소 홉 + 10) (6x6 (0,0) → (5,5)는 70 ms, 20홉). `P.deadlineScale`, `P.ttlScale`, `P.deadlineMargin`, `P.ttlMargin`
- **배경 트래픽:** 모든 링크에 기본 부하(용량의 0.1~0.4배) + 지역 핫스팟(중심 위성 송신 링크에 용량의 0.5~1.5배, 이웃 위성은 그 절반, 평균 1초). 측정 흐름이 지나는 지역이 3배 더 잘 뽑힘 (`sim/bg_event.py`)
- **혼잡 단계:** 6x6 기준 핫스팟 발생 간격 평균 base 1초, high 0.5초, severe 0.25초 (동시에 걸린 지역 약 1, 2, 4개). 위성 수에 비례해 더 자주 생김 (6x11은 1.8배). 학습은 high : severe = 1 : 2
- **시드:** 최종 평가 1~20, 학습 중 검증 501~503, 학습 1001부터, 적응 2001부터 (서로 겹치지 않음)

자세한 내용: `docs/README_isl.md` (사용법), `docs/flow.md` (코드 흐름), `docs/csv.md` (CSV 열), `docs/simulation_instructions.md` (시뮬레이션 설명), `docs/variables_isl.md` (변수), `rl/README.md` (강화학습)
