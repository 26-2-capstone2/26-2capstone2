# 26-2capstone2

명지대학교 26-2 캡스톤디자인2: 실시간 UDP 트래픽을 위한 강화학습 기반 LEO 위성 라우팅 (연속 패킷 손실 최소화)

## 노션 링크

https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## ISL 라우팅 시뮬레이터 (`isl_routing/`)

LEO 위성 사이 링크(ISL)에서 출발 위성 (0,0) → 도착 위성 (5,5)로 실시간 UDP 패킷(초당 60개, 160 Byte, 기한 70 ms)을 보내고, 라우팅이 혼잡을 피해 **연속 패킷 손실을 줄이고 기한 내 도착률을 높이는지** 비교하는 Python 시뮬레이션.

| 라우팅 | 방식 |
| --- | --- |
| `routeA` | Dijkstra 최단 경로 (링크 지연만 봄, 기준선) |
| `routeB` | DRA (Ekici et al. 2001, 자기 송신 큐가 차면 보조 방향) |
| `routeC` | 강화학습 (Double DQN, 위성들이 신경망 하나를 공유하는 CTDE) |

- **망 구조:** 6x6 가상 격자 (기본), 크기를 바꾼 격자, Iridium, Starlink (`ISL_TOPOLOGY` 환경 변수)
- **배경 트래픽:** 모든 링크에 기본 부하 + 지역 핫스팟이 무작위로 생겼다 사라짐 (`P.bgMode = 'event'`, 기존 고정 핫스팟 방식은 `'hotspot'`)
- **혼잡 단계:** `base`, `high`, `severe` (핫스팟 발생 빈도로 구분, severe는 최악 상황)
- **에피소드:** 10초. 학습 시드 1001부터, 검증 시드 501~505, 최종 평가 시드 1~20
- **연속 손실:** 기한 안에 도착하지 못한 패킷이 패킷 번호 순서로 3개 이상 이어진 구간

| 문서 | 내용 |
| --- | --- |
| [`isl_routing/README.md`](isl_routing/README.md) | 설치, 실행 명령, 망 구조 |
| [`flow.md`](flow.md) | 코드가 어떤 순서로, 어떤 파일을 거쳐 돌아가는지 (시뮬레이션, 학습, 평가) |
| [`csv.md`](csv.md) | 결과 CSV 각 열의 뜻 |
| [`isl_routing/rl/README.md`](isl_routing/rl/README.md) | 강화학습 과정 (State, Action, Reward, 학습 설정) |
| [`isl_routing/docs/README_isl.md`](isl_routing/docs/README_isl.md) | 자세한 사용법, 파일별 역할 |
| [`isl_routing/docs/simulation_instructions.md`](isl_routing/docs/simulation_instructions.md) | 시뮬레이션이 하는 일과 결과 파일 요약 |
| [`isl_routing/docs/variables_isl.md`](isl_routing/docs/variables_isl.md) | 모든 변수 설명 |
| [`isl_routing/rl/학습안정화_기록.md`](isl_routing/rl/학습안정화_기록.md) | 학습 안정화 테스트 기록 |

## 폴더 구조

```
isl_routing/
  run.py             터미널 실행 도우미 (번호로 골라 실행, 가장 쉬운 방법)
  main_isl.py        A, B 시뮬레이션 실행 + 결과 저장
  eval_routes.py     A, B, C 최종 평가 (평가 시드별 결과 포함)
  config_isl.py      시뮬레이터 설정값 (망, 큐, 기한, 배경 트래픽, 혼잡 단계)
  run_batch.py       여러 세트 한 번에 실행
  show_results.py    결과 보기
  show_node.py       노드 보기
  check_bg.py        배경 트래픽 점검
  sim/               시뮬레이터 본체, 망 구조, 배경 트래픽, 링크 기록
  routing/           라우팅 route_A, route_B, route_C (입력과 출력이 같아서 바꿔 끼움)
  rl/                강화학습 설정, State, 보상, DQN, 경험 연결, 학습
  analysis/          성능 지표, 연속 손실, 학습 곡선 목표 판정, 최종 성능 목표 판정
  viz/               그래프, 애니메이션
  web/               웹 시뮬레이터 화면
  tests/             강화학습 계산 확인 테스트
  docs/              사용법, 변수 설명
```

## 빠른 시작

```bash
cd isl_routing
pip install -r requirements.txt
python run.py
```

질문에 번호로 답하면 됨 (할 일, 망 구조, 혼잡 단계, 라우팅, 시드, 에피소드 수). 엔터만 누르면 기본값.

| 할 일 | 명령 (isl_routing 폴더에서) |
| --- | --- |
| A, B 시뮬레이션 | `python main_isl.py` |
| C 학습 (학습 시드 0) | `python rl/train_rl.py 270 0 0` |
| 학습 곡선 목표 판정 | `python analysis/learning_targets.py 학습폴더 [학습폴더 ...]` |
| A, B, C 최종 평가 | `python eval_routes.py 모델0,모델1,모델2` |
| 최종 성능 목표 판정 | `python analysis/compare_runs.py 평가폴더` |
| 테스트 | `python -m unittest discover -s tests` |

## 결과 저장 위치 (프로젝트 밖, 홈 폴더)

- 시뮬레이션 결과: `~/isl_saved_runs/라우팅_혼잡단계_날짜/`
- 학습된 모델과 학습 기록: `~/rl_models/routeC_날짜_s학습시드/`
- 최종 평가 결과: `~/isl_saved_runs/eval_날짜/`
- 다른 곳에 저장하려면 환경 변수 `ISL_SAVE_ROOT`(시뮬레이션, 평가), `RL_SAVE_ROOT`(학습)

MATLAB 버전(`ISL-MATLAB` 브랜치)과 변수명은 같지만, 배경 트래픽, 에피소드, 혼잡 단계, 강화학습은 Python 버전에만 있음.
