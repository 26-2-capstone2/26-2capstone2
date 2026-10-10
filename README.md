# 26-2capstone2

명지대학교 26-2 캡스톤디자인2

## 노션 링크

https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## ISL-Python 사용법

6x6 Grid ISL에서 출발 위성 (0,0) → 도착 위성 (5,5)로 10분 동안 패킷을 보내고, 라우팅이 혼잡을 얼마나 잘 피해 기한 안에 도착시키는지 측정하는 Python 시뮬레이션.

- 라우팅: **route_A** (최단 경로, 부하 무시 - 기준선) / **route_B** (부하 고려, Liu et al. 단순화)
- 배경 트래픽: 송신 큐 핫스팟 (위성 하나의 한 방향 큐가 과부하). 에피소드마다 개수, 위치, 세기가 무작위
- 에피소드: 30초 x 20개 = 10분. 에피소드마다 다른 시드(혼잡 지도)를 씀
- 결과: 성능 지표 7개, 패킷과 결정과 노드 기록 CSV, 그래프, 애니메이션 (결정 기록은 강화학습 학습 데이터)

MATLAB 버전(`ISL-MATLAB` 브랜치)과 파일명, 변수명이 같음. 배경 트래픽, 에피소드, route_A, 노드 기록은 Python 버전에만 있어 결과는 다름.

| 문서 | 내용 |
| --- | --- |
| [`flow.md`](flow.md) | 코드가 어떤 순서로, 어떤 파일을 거쳐 돌아가는지 |
| [`csv.md`](csv.md) | 결과 CSV 각 열의 뜻 |
| `isl_6x6_routing_py/simulation_instructions.py` | 시뮬레이션이 하는 일과 결과 파일 요약 |
| `isl_6x6_routing_py/variables_isl.py` | 모든 변수 설명 |
| `isl_6x6_routing_py/README_isl.py` | 자세한 사용법 |

### 준비

```bash
pip install numpy matplotlib pillow
```

### 실행

1. VS Code에서 `isl_6x6_routing_py` 폴더 열기
2. 라우팅 정하기: `config_isl.py`의 `P.routeName = 'routeA'` 또는 `'routeB'`
3. `main_isl.py`를 열고 오른쪽 위 ▶ **Run Python File** 클릭
   ```bash
   python main_isl.py
   ```
   ε = 0 (성능 측정용), ε = 0.1 (데이터 수집용) 두 번, 각각 에피소드 20개를 실행. 터미널에 에피소드별 핫스팟 목록과 `[rate60pps_eps0.0]`, `[rate60pps_eps0.1]` 결과가 나오면 완료
   - 배경 시작 시드를 바꾸려면 `python main_isl.py 7`처럼 숫자를 붙이면 됨 (에피소드 e는 시작 시드 + e)
4. 결과 보기
   ```bash
   python show_results.py
   ```
   지표 표(터미널), 지표 비교 그래프, 실행 분석 그래프, 노드 그림, 애니메이션 창이 뜸
5. 원하는 노드 (p,s) 자세히 보기
   ```bash
   python show_node.py 5 2
   ```
6. 배경 트래픽 검증 (선택)
   ```bash
   python check_bg.py check
   ```

### 결과 파일

`isl_6x6_routing_py/results/` 폴더에 생성 (용량 때문에 git에는 올리지 않음)

| 파일 | 내용 |
| --- | --- |
| `metrics_summary.csv` / `.png` | 성능 지표 7개 + 손실 원인별 개수 + 배경 개수 |
| `run_analysis.png` | 지연 분포, 시간별 변화, 링크 사용량 지도, 홉 수, 선택 유형, 손실 원인 |
| `node_map_*.png` | 6x6 노드별 요약 지도 (큐, 보낸 수, 오버플로, 기한 초과) |
| `node_time_*.png` | 주 흐름 손실이 가장 많은 노드의 시간 변화 |
| `anim_*.gif` | 첫 에피소드의 처음 0.2초 애니메이션 (링크 큐 색 + 이동 중 패킷) |
| `packet_log_*.csv` | 패킷 1개 = 1줄 (생성과 종료 시각, 결과, 홉 수, 에피소드) |
| `decision_log_*.csv` | 라우팅 결정 1번 = 1줄 (강화학습 학습용 데이터, ε = 0.1만) |
| `node_log_*.csv` | 0.1초마다 노드 1개 = 1줄 (노드 기준 큐, 보낸 수, 손실) |
| `bg_scenario.csv` | 에피소드별 핫스팟 목록 (위치, 방향, 세기) |

열 설명은 [`csv.md`](csv.md) 참고.

### 결과 저장 경로

실행이 끝나면 결과와 코드가 홈 폴더의 `isl_saved_runs\날짜_시분` 폴더에 자동 복사됨 (예: `C:\Users\eun\isl_saved_runs\2026-10-10_1320`).
다른 곳에 저장하려면 환경변수 `ISL_SAVE_ROOT`에 경로를 지정.

### 설정값 변경

`config_isl.py`만 수정하면 됨.

| 바꿀 것 | 변수 |
| --- | --- |
| 네트워크 (큐 200, 링크 용량 5, 지연) | `P.queueMax`, `P.linkCapacity`, `P.linkDelay` |
| 패킷 (기한 70, TTL 20, 60개/초) | `P.deadline`, `P.ttlInit`, `P.genRate` |
| 라우팅 선택, B의 k, X, Y | `P.routeName`, `P.k`, `P.X`, `P.Y` |
| 에피소드 (30초 x 20개) | `P.simTime`, `P.numEpisodes` |
| 배경 트래픽 (핫스팟 2~5개, 세기 0.7~2.0배, ON 150 / OFF 750 step, 시작 시드) | `P.bg...` |

모든 변수 설명은 `variables_isl.py`, 자세한 사용법은 `README_isl.py` 참고.
