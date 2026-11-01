# ISL 6x6 라우팅 시뮬레이션 + 강화학습

명지대학교 26-2 캡스톤디자인2

LEO 위성 6 x 6 격자(ISL)에서 실시간 UDP 패킷을 보낼 때, **연속 패킷 손실을 줄이고 기한 내 도착률을 높이는** 라우팅을 비교함.

| 라우팅 | 방식 |
|---|---|
| routeA | 정적 최단 경로 (링크 지연만 봄, 기준선) |
| routeB | DRA (자기 송신 큐만 보고 주/보조 방향 선택) |
| routeC | 강화학습 (Double DQN, 위성 36개가 신경망 하나를 공유하는 CTDE) |

노션: https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## 설치

```
pip install -r requirements.txt
```

torch는 강화학습(routeC)을 학습하거나 평가할 때만 필요함.

## 실행 (이 폴더에서)

**가장 쉬운 방법: `python run.py`**
질문에 번호로 답하면 됨 (할 일, grid 구조, 혼잡 단계, 라우팅, 시드, 에피소드 수). 엔터만 누르면 기본값을 씀.
아래 명령을 직접 쓸 수도 있음.

| 할 일 | 명령 |
|---|---|
| A, B 비교 실행 (config_isl.py 설정대로) | `python main_isl.py` |
| 시드, 혼잡 단계, 라우팅 지정 | `python main_isl.py 1001 high routeB` |
| 학습된 C로 실행 | `python main_isl.py 1 severe routeC 모델경로/model_final.pt` |
| 강화학습 C 학습 | `python rl/train_rl.py` (짧게 시험: `python rl/train_rl.py 3 5000`) |
| A, B, C 평가 (평가 시드 1~20 x 혼잡 3단계) | `python eval_routes.py 모델경로/model_final.pt` |
| 여러 세트 한 번에 실행 | `python run_batch.py high routeB 1001 5` |
| 테스트 | `python -m unittest discover -s tests` |
| 웹 시뮬레이터 | `python web/server.py` 후 http://localhost:8000 |

grid 구조 바꾸기: 환경 변수 `ISL_TOPOLOGY`로 고름 (기본은 6x6 가상 격자, `sim/topology.py`)

| 값 | 구조 |
|---|---|
| `grid` (기본) | 6 x 6 가상 격자, 끝은 막힘, 지연 상하 7 / 좌우 2 ms |
| `grid:8x8` 등 | 크기를 바꾼 가상 격자 |
| `iridium` | 6 x 11, 같은 궤도 원형, seam(1번과 6번 궤도면 사이) 없음, 위도 60도 이상 옆 궤도 링크 꺼짐, 거리 기반 지연 |
| `starlink` | 72 x 22, 같은 궤도와 옆 궤도 모두 원형, 거리 기반 지연 |
| `starlink:12x12` 등 | Starlink 축소판 |

예) PowerShell: `$env:ISL_TOPOLOGY="iridium"; python rl/train_rl.py`, bash: `ISL_TOPOLOGY=iridium python rl/train_rl.py`
기한과 TTL은 구조에 맞게 자동으로 정해지고, 결과 폴더 이름에 구조 이름이 붙음 (예: `routeC_iridium_날짜`)

결과 저장 위치 (프로젝트 밖, 홈 폴더)
- 시뮬레이션 결과: `~/isl_saved_runs/라우팅_혼잡단계_날짜/`
- 학습된 모델: `~/rl_models/routeC_날짜/`

## 폴더 구조

```
main_isl.py        시뮬레이션 실행 (결과 CSV, 그래프, 애니메이션 저장)
config_isl.py      시뮬레이터 설정값, 혼잡 단계 base / high / severe
eval_routes.py     A, B, C를 같은 조건으로 평가
run_batch.py       시드를 바꿔 여러 세트 실행
check_bg.py, show_node.py, show_results.py   배경 트래픽, 노드 기록, 결과 확인용

routing/    라우팅 함수 route_A, route_B, route_C (입력과 출력이 같아서 바꿔 끼움)
sim/        시뮬레이터 본체, 격자, 배경 트래픽, 에피소드 합치기, 노드 기록, 링크 기록
analysis/   성능 지표, 연속 손실 판정, 결과 저장
rl/         강화학습 설정, State 24개, 보상, DQN, 경험 연결, 학습
viz/        그래프, 애니메이션, 학습 곡선
docs/       변수 설명, 실행 안내
tests/      강화학습 계산 확인 테스트
web/        웹 시뮬레이터 대시보드
```

## 주요 정의

- **연속 손실:** 패킷 번호 순서로 손실이 3개 이상 이어진 구간 (`analysis/burst_loss.py`)
- **손실:** 기한 내에 도착하지 못한 모든 패킷 (목적지 기한 초과, 중간 기한 초과, 큐 넘침, TTL 만료)
- **혼잡 단계:** 배경 트래픽 핫스팟 개수와 켜져 있는 비율로 나눔 (base 약 1/6, high 약 1/3, severe 약 1/2)
- **시드:** 평가 1~20, 학습 1001부터 (평가 시드는 학습에 쓰지 않음)
