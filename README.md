# 26-2capstone2

명지대학교 26-2 캡스톤디자인2

## 노션 링크

https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## ISL-MATLAB 사용법

6x6 Grid ISL에서 출발 위성 (0,0) → 도착 위성 (5,5)로 패킷을 보내고, 라우팅으로 경로를 정하는 MATLAB 시뮬레이션

### 실행

1. MATLAB에서 `isl_6x6_routing` 폴더로 이동
   ```matlab
   cd('C:\...\26-2capstone2\isl_6x6_routing')
   ```
2. 시뮬레이션 실행 (약 3~4분)
   ```matlab
   main_isl
   ```
   명령 창에 `[rate60pps_eps0.0]`, `[rate60pps_eps0.1]` 두 줄과 결과 표가 나오면 완료
3. 결과 보기
   ```matlab
   show_results
   ```
   지표 표, 지표 비교 그래프, 실행 분석 그래프, 애니메이션 창이 뜸

### 결과 파일

`isl_6x6_routing/results/` 폴더에 생성됩니다. (용량 때문에 git에는 올리지 않음)

| 파일 | 내용 |
| --- | --- |
| `metrics_summary.png` | 성능 지표 7개 비교 |
| `run_analysis.png` | 지연 분포, 시간별 변화, 링크 사용량 지도, 홉 수, 선택 유형, 손실 원인 |
| `anim_*.gif` | 0~200 ms 애니메이션 |
| `metrics_summary.csv` | 성능 지표 숫자 |
| `packet_log_*.csv` | 패킷 1개 = 1줄 (생성·종료 시각, 결과, 홉 수) |
| `decision_log_*.csv` | 라우팅 결정 1번 = 1줄 (강화학습 학습용 데이터) |

### 결과 저장 경로

실행이 끝나면 결과와 코드가 날짜별 폴더(`yyyy-MM-dd_HHmm`)에 자동 복사.
`main_isl.m` 맨 아래 `saveRoot`를 본인 PC 경로로 바꿔서 사용.

```matlab
saveRoot = 'C:\Users\eun\Desktop\capstone_isl\baseline';   % 본인 경로로 변경
```

### 설정값 변경

`config_isl.m` 수정. (생성률, 패킷 크기, 총 시간, k·X·Y 등)
모든 변수 설명은 `variables_isl.m`, 자세한 사용법은 `README_isl.m` 참고.
