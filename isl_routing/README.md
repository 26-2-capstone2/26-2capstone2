# ISL 라우팅 시뮬레이션 + 강화학습

명지대학교 26-2 캡스톤디자인2

LEO 위성 사이 링크(ISL)에서 실시간 UDP 패킷을 보낼 때, **연속 패킷 손실을 줄이고 기한 내 도착률을 높이는** 라우팅을 비교함.

| 라우팅 | 방식 |
|---|---|
| routeA | Dijkstra 최단 경로 (링크 지연만 봄, 기준선) |
| routeB | DRA (자기 송신 큐가 차면 보조 방향) |
| routeC | 강화학습 (Double DQN, 위성들이 신경망 하나를 공유하는 CTDE) |

노션: https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## 설치

```
pip install -r requirements.txt
```

torch는 강화학습(routeC)을 학습하거나 평가할 때만 필요함.

## 실행 (이 폴더에서)

**가장 쉬운 방법: `python run.py`**
질문에 번호로 답하면 됨 (할 일, 망 구조, 혼잡 단계, 라우팅, 시드, 에피소드 수, 학습 시드). 엔터만 누르면 기본값.

| 할 일 | 명령 |
|---|---|
| B 실행 (A는 라우팅 인자로) | `python main_isl.py` |
| 시드, 혼잡 단계, 라우팅 지정 | `python main_isl.py 1 severe routeB` |
| 학습된 C로 실행 | `python main_isl.py 1 severe routeC 모델경로/model_final.pt` |
| C 학습 (에피소드 수, 길이 0 = 기본, 학습 시드) | `python rl/train_rl.py 80 0 0` (짧게 시험: `python rl/train_rl.py 3 2000 0`) |
| 학습 곡선 목표 판정 | `python analysis/learning_targets.py 학습폴더 [학습폴더 ...]` |
| B, C 최종 평가 (평가 시드 1~20 x 혼잡 3단계) | `python eval_routes.py 모델0,모델1,모델2` |
| 최종 성능 목표 판정 | `python analysis/compare_runs.py 평가폴더` |
| 여러 세트 한 번에 실행 | `python tools/run_batch.py high routeB 1001 5` |
| 테스트 | `python -m unittest discover -s tests` |
| 웹 시뮬레이터 | `python web/server.py` 후 http://localhost:8000 |

학습 시드 3개를 동시에 돌리려면 터미널 3개에서 마지막 숫자만 0, 1, 2로 바꿔 실행.

망 구조 바꾸기: 환경 변수 `ISL_TOPOLOGY` (기본은 6x6 가상 격자, `sim/topology.py`)

| 값 | 구조 |
|---|---|
| `grid` (기본) | 6 x 6 가상 격자, 끝은 막힘, 지연 상하 7 / 좌우 2 ms |
| `grid:8x8` 등 | 크기를 바꾼 가상 격자 |
| `iridium` | 6 x 11, 같은 궤도면 안은 원형, 첫째와 마지막 궤도면 사이는 끊김(seam), 고위도에서 옆 궤도면 링크 꺼짐, 거리 기반 지연 |
| `starlink` | 72 x 22, 같은 궤도와 옆 궤도 모두 원형, 거리 기반 지연 |
| `starlink:12x12` 등 | Starlink 축소판 |

예) PowerShell: `$env:ISL_TOPOLOGY="iridium"; python rl/train_rl.py`, bash: `ISL_TOPOLOGY=iridium python rl/train_rl.py`
기한과 TTL은 구조에 맞게 자동으로 정해지고, 결과 폴더 이름에 구조 이름이 붙음.

결과 저장 위치 (프로젝트 밖, 홈 폴더)
- 시뮬레이션 결과: `~/isl_saved_runs/라우팅_혼잡단계_날짜/`
- 학습된 모델과 학습 기록: `~/rl_models/routeC_날짜_s학습시드/`
- 최종 평가: `~/isl_saved_runs/eval_날짜/`

## 폴더 구조

```
run.py             터미널 실행 도우미
main_isl.py        A, B 시뮬레이션 실행 (결과 CSV, 그래프, 애니메이션 저장)
config_isl.py      시뮬레이터 설정값, 배경 트래픽, 혼잡 단계
eval_routes.py     B, C를 같은 조건으로 평가 (A 선택 가능) (평가 시드별 결과 포함)
tools/             보조 실행 파일: run_batch (여러 세트 실행), show_results (결과 보기), show_node (노드 보기), check_bg (배경 트래픽 점검)

routing/    라우팅 route_A, route_B, route_C (입력과 출력이 같아서 바꿔 끼움)
sim/        시뮬레이터 본체, 망 구조, 배경 트래픽(bg_event 새 방식, bg_traffic 기존 방식), 에피소드 합치기, 노드 기록, 링크 기록
analysis/   성능 지표, 연속 손실, 학습 곡선 목표 판정, 최종 성능 목표 판정, 결과 저장
rl/         강화학습 설정, State 15개, 보상, DQN, 경험 연결, 학습, 학습 안정화 기록
viz/        그래프, 애니메이션, 학습 곡선
docs/       사용법, 시뮬레이션 설명, 변수 설명
tests/      강화학습 계산 확인 테스트
web/        웹 시뮬레이터 대시보드
```

## 주요 정의

- **손실:** 기한 내에 도착하지 못한 모든 패킷 (목적지 기한 초과, 중간 기한 초과, 큐 넘침, TTL 만료)
- **연속 손실:** 패킷 번호 순서로 손실이 3개 이상 이어진 구간 (에피소드 경계에서 끊음, `analysis/burst_loss.py`)
- **배경 트래픽:** 모든 링크에 기본 부하(용량의 0.1~0.4배) + 지역 핫스팟(중심 위성과 이웃 위성의 송신 링크, 평균 2.5초)이 무작위로 생겼다 사라짐 (`sim/bg_event.py`)
- **혼잡 단계:** 핫스팟 발생 간격 평균 base 1초, high 0.5초, severe 0.25초, 지속 평균 1초 (동시에 걸린 지역 약 1, 2, 4개)
- **주 흐름:** 4개 (흐름 0 (0,0) → (5,5) + 무작위 3개, 흐름마다 초당 60개). 학습 때는 흐름 0도 무작위, 검증과 평가는 (0,0) → (5,5)
- **시드:** 최종 평가 1~20, 학습 중 검증 501~505, 학습 1001부터 (서로 겹치지 않음)

자세한 내용: `docs/README_isl.md` (사용법), `docs/simulation_instructions.md` (시뮬레이션 설명), `docs/variables_isl.md` (변수), `rl/README.md` (강화학습)
