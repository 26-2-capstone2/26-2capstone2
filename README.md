# 26-2capstone2

명지대학교 26-2 캡스톤디자인2: 실시간 UDP 트래픽을 위한 강화학습 기반 LEO 위성 라우팅 (연속 패킷 손실 최소화)

## 노션 링크

https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## ISL 라우팅 시뮬레이터 (`isl_routing/`)

LEO 위성 사이 링크(ISL)에서 실시간 UDP 흐름 4개를 보내고, 라우팅이 혼잡을 피해 **측정 흐름(흐름 0)의 연속 패킷 손실을 줄이고 기한 내 도착률을 높이는지** 비교하는 Python 시뮬레이션.

| 라우팅 | 방식 |
| --- | --- |
| `routeA` | Dijkstra 최단 경로 (링크 지연만 봄, 기준선) |
| `routeB` | DRA (Ekici et al. 2001, 자기 송신 큐가 차면 보조 방향) |
| `routeC` | 강화학습 (Double DQN, 위성들이 신경망 하나를 공유하는 CTDE) |

- **망:** 끝이 막힌 직사각형 가상 격자만 씀 (11/26 회의). 실제 위성군 이름(`iridium`, `starlink`)은 위성 수만 같은 격자(6x11, 72x22)로 바뀜. 링크 지연 상하 7, 좌우 2 ms 고정
- **흐름:** 4개, 흐름마다 초당 60개, 160 Byte
  - 흐름 0 = 측정 흐름: 시험 때 (0,0) → 격자 끝 모서리 고정, 학습 때는 그 거리 근처 쌍 중 무작위. **모든 성능 지표는 이 흐름 기준**
  - 흐름 1~3 = 다른 GSL 흐름: 짧은, 중간, 먼 거리를 고르게 섞은 무작위 쌍 (트래픽 역할)
  - 기한, TTL은 흐름마다 그 흐름 거리로 정함 (최소 지연 + 25 ms, 최소 홉 + 10)
- **배경 트래픽:** 모든 링크에 기본 부하 + 지역 핫스팟이 무작위로 생겼다 사라짐. 위성 수에 비례해 더 자주 생김
- **혼잡 단계:** `base`, `high`, `severe` (핫스팟 발생 빈도로 구분)
- **실험 순서:** 학습 (기본 10x10 격자) → 적응 (평가할 격자에서 5 에피소드) → 최종 평가 (평가 시드 1~20, DRA와 비교)
- **연속 손실:** 같은 흐름 안에서 패킷 번호 순서로 손실이 3개 이상 이어진 구간

| 문서 | 내용 |
| --- | --- |
| [`isl_routing/README.md`](isl_routing/README.md) | 설치, 실행 명령, 망 구조, 주요 정의 |
| [`isl_routing/docs/flow.md`](isl_routing/docs/flow.md) | 코드가 어떤 순서로, 어떤 파일을 거쳐 돌아가는지 (시뮬레이션, 학습, 적응, 평가) |
| [`isl_routing/docs/csv.md`](isl_routing/docs/csv.md) | 결과 CSV 각 열의 뜻 |
| [`isl_routing/rl/README.md`](isl_routing/rl/README.md) | 강화학습 과정 (State, Action, Reward, 학습 설정) |
| [`isl_routing/docs/README_isl.md`](isl_routing/docs/README_isl.md) | 자세한 사용법, 파일별 역할 |
| [`isl_routing/docs/simulation_instructions.md`](isl_routing/docs/simulation_instructions.md) | 시뮬레이션이 하는 일과 결과 파일 요약 |
| [`isl_routing/docs/variables_isl.md`](isl_routing/docs/variables_isl.md) | 모든 변수 설명 |
| [`isl_routing/rl/학습안정화_기록.md`](isl_routing/rl/학습안정화_기록.md) | 학습 테스트 기록 (11/26 통합 전까지의 실험 포함) |

## 폴더 구조

```
isl_routing/
  run.py             터미널 실행 도우미 (번호로 골라 실행, 가장 쉬운 방법)
  main_isl.py        시뮬레이션 실행 + 결과 저장 (기본 B, A, C 선택 가능)
  eval_routes.py     B, C 최종 평가 (A는 고를 때만, 평가 시드별 결과 포함)
  config_isl.py      시뮬레이터 설정값 (망, 큐, 흐름, 기한, 배경 트래픽, 혼잡 단계)
  sim/               시뮬레이터 본체, 망 구조, 흐름, 배경 트래픽, 링크 기록
  routing/           라우팅 route_A, route_B, route_C (입력과 출력이 같아서 바꿔 끼움)
  rl/                강화학습 설정, State, 보상, DQN, 경험 연결, 학습, 적응
  analysis/          성능 지표, 측정 흐름 골라내기, 연속 손실, 학습 곡선 목표 판정, 최종 성능 목표 판정
  viz/               그래프, 애니메이션, 흐름별 결과, 학습 곡선 비교
  tools/             보조 실행 파일 (여러 세트 실행, 결과 보기, 노드 보기, 배경 트래픽 점검)
  tests/             흐름, 강화학습 계산 확인 테스트
  docs/              사용법, 코드 흐름, CSV 설명, 변수 설명
```

## 빠른 시작

```bash
cd isl_routing
pip install -r requirements.txt
python run.py
```

질문에 번호로 답하면 됨 (할 일, 격자, 혼잡 단계, 라우팅, 시드, 에피소드 수). 엔터만 누르면 기본값. 직접 명령은 [`isl_routing/README.md`](isl_routing/README.md) 참고.

## 결과 저장 위치 (프로젝트 밖, 홈 폴더)

- 시뮬레이션 결과: `~/isl_saved_runs/라우팅_혼잡단계_날짜/`
- 학습된 모델과 학습 기록: `~/rl_models/routeC_격자_날짜_s학습시드/`, 적응한 모델: `~/rl_models/routeC_adapt_..._to_격자_날짜/`
- 최종 평가 결과: `~/isl_saved_runs/eval_날짜/`
- 다른 곳에 저장하려면 환경 변수 `ISL_SAVE_ROOT`(시뮬레이션, 평가), `RL_SAVE_ROOT`(학습)

GSL(지상국에서 첫 수신 위성까지)은 `GSL` 브랜치의 MATLAB 코드. ISL과의 연결은 아직 반영하지 않음.
