# 26-2capstone2

명지대학교 26-2 캡스톤디자인2

## 노션 링크

https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## ISL-Python 사용법

6x6 Grid ISL에서 출발 위성 (0,0) → 도착 위성 (5,5)로 10분 동안 패킷을 보내고, 라우팅이 혼잡을 얼마나 잘 피해 기한 안에 도착시키는지 측정하는 Python 시뮬레이션.

- 라우팅: **route_A** (최단 경로, 부하 무시 - 기준선) / **route_B** (부하 고려, Liu et al. 단순화)
- 배경 트래픽: 주 흐름 경로에 일부러 혼잡을 만드는 흐름 4개 (부하 단계: 없음 / 낮음 / 중간 / 높음 / 매우 높음)
- 결과: 성능 지표 7개, 패킷·결정·노드 기록 CSV, 그래프, 애니메이션 (결정 기록은 강화학습 학습 데이터)

MATLAB 버전(`ISL-MATLAB` 브랜치)과 파일명·변수명이 같음. 배경 트래픽, route_A, 여러 시드 실험, 노드 기록은 Python 버전에만 있어 결과는 다름.

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

### 실험 1번 (단일 실험)

1. VS Code에서 `isl_6x6_routing_py` 폴더 열기
2. 무엇을 돌릴지 정하기
   - 라우팅: `config_isl.py`의 `P.routeName = 'routeA'` 또는 `'routeB'`
   - 배경 부하·시드: `config_bg.py`의 `B.mainLevel` (`'none'`, `'low'`, `'mid'`, `'high'`, `'extreme'`), `B.mainSeed` (기본 1001)
3. `main_isl.py`를 열고 오른쪽 위 ▶ **Run Python File** 클릭 (약 10분)
   ```bash
   python main_isl.py
   ```
   ε = 0 (성능 측정용), ε = 0.1 (데이터 수집용) 두 번 실행. 터미널에 `[rate60pps_eps0.0]`, `[rate60pps_eps0.1]`과 결과가 나오면 완료
4. 결과 보기
   ```bash
   python show_results.py
   ```
   지표 표(터미널), 지표 비교 그래프, 실행 분석 그래프, 노드 그림, 애니메이션 창이 뜸
5. 원하는 노드 (p,s) 자세히 보기
   ```bash
   python show_node.py 5 2
   ```

### 여러 시드 실험 (평균 ± 편차)

시드 하나의 결과는 "배경이 우연히 그렇게 켜졌을 때"의 한 경우라서, 부하 단계마다 시드 여러 개로 돌려 평균 ± 표준편차로 비교.

1. `config_bg.py` 아래쪽 on/off 설정
   - `B.runLevels`: 돌릴 부하 단계 (기본 낮음·중간·높음)
   - `B.runEval`: 평가 (ε = 0, 평가용 시드 101~110)
   - `B.runTrain`: 학습 데이터 수집 (ε = 0.1, 학습용 시드 1~10, 실행 1번당 decision_log 약 30 MB)
   - `B.numSeeds`, `B.numWorkers`: 시드 수, 동시에 돌릴 개수
2. 실행 (부하 3단계 x 시드 10개 = 30번, 동시 6개면 약 30분)
   ```bash
   python run_experiments.py
   ```

학습용과 평가용 시드를 나눈 이유: 강화학습이 처음 보는 혼잡 패턴에서도 잘해야 "외워서 잘한 게 아니다"라고 말할 수 있음.

### 결과 파일

`isl_6x6_routing_py/results/` 폴더에 생성됩니다. (용량 때문에 git에는 올리지 않음)

| 파일 | 내용 |
| --- | --- |
| `metrics_summary.csv` / `.png` | 성능 지표 7개 + 손실 원인별 개수 + 배경 개수 |
| `run_analysis.png` | 지연 분포, 시간별 변화, 링크 사용량 지도, 홉 수, 선택 유형, 손실 원인 |
| `node_map_*.png` | 6x6 노드별 요약 지도 (큐, 보낸 수, 오버플로, 기한 초과) |
| `node_time_*.png` | 주 흐름 손실이 가장 많은 노드의 시간 변화 |
| `anim_*.gif` | 처음 3초 애니메이션 (링크 큐 색 + 이동 중 패킷) |
| `packet_log_*.csv` | 패킷 1개 = 1줄 (생성·종료 시각, 결과, 홉 수) |
| `decision_log_*.csv` | 라우팅 결정 1번 = 1줄 (강화학습 학습용 데이터, ε = 0.1만) |
| `node_log_*.csv` | 0.1초마다 노드 1개 = 1줄 (노드 기준 큐·보낸 수·손실) |
| `run_info.txt` | 실행 시각, 라우팅, 배경 부하, 시드 |
| `experiments/` | `run_experiments.py` 여러 시드 요약 (`eval_runs.csv`, `eval_stats.csv`, `eval_summary.png`, `conditions.txt`) |

열 설명은 [`csv.md`](csv.md) 참고.

### 결과 저장 경로

실행이 끝나면 결과와 코드가 `라우팅알고리즘\시드종류\라우팅알고리즘_부하단계_시드` 폴더에 자동 복사.

```
baseline_py\
  routeA \ routeB \ routeC
    baseline \ train \ evaluation        <- 학습용 시드 1~10 → train, 평가용 101~110 → evaluation, 그 외 → baseline
      routeB_mid_102\code, results       <- 실행 1개
      routeB_summary_low-mid-high\       <- 여러 시드 요약
```

예) `main_isl.py` 기본 (route_B, 높음, 시드 1001) → `baseline_py\routeB\baseline\routeB_high_1001`
같은 이름으로 다시 돌리면 같은 이름의 파일은 덮어씀. `save_results.py` 맨 위 `SAVE_ROOT`를 본인 PC 경로로 바꿔서 사용.

```python
SAVE_ROOT = r'C:\Users\eun\Desktop\capstone_isl\baseline_py'   # 본인 경로로 변경
```

### 설정값 변경

| 바꾸고 싶은 것 | 파일 |
| --- | --- |
| 네트워크 (큐 200, 링크 용량 5, 지연), 패킷 (기한 90, TTL 20, 60개/초), 라우팅 선택, B의 k·X·Y | `config_isl.py` |
| 배경 흐름, 부하 단계 값, 시드, 단일 실험 단계·시드, 여러 시드 실험 on/off | `config_bg.py` |
| 결과 저장 경로 | `save_results.py` 맨 위 `SAVE_ROOT` |

모든 변수 설명은 `variables_isl.py`, 자세한 사용법은 `README_isl.py` 참고.
