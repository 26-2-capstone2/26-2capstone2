import csv,sys
from pathlib import Path
root=Path(sys.argv[1])
with (root/'runs.csv').open(encoding='utf-8-sig',newline='') as f:runs=list(csv.DictReader(f))
with (root/'summary.csv').open(encoding='utf-8-sig',newline='') as f:stats={x['metric']:x for x in csv.DictReader(f)}
labels={'loss_pct':'패킷 손실률 (%)','onTime_pct':'기한 내 도착률 (%)','maxLossRun':'최대 연속 손실 (개)','handovers':'핸드오버 (회)'}
text='''# DDQN 6×11 · 6 dB 평가 결과

지상국→선택된 첫 위성까지만 계산했다. 기존 방식·최대 SNR 비교는 이번에 실행하지 않았다.

## 실행 조건과 학습

- 66개 위성(6×11), 환경감쇠 6 dB, 600초, 160 B·60 pps = 36,000개/회, 도착 기한 20 ms.
- 툴박스 QPSK·AR4JA·AWGN 측정 표 유지. 송수신 조건과 PHY 값을 결과에 맞춰 수정하지 않았다.
- 기존 10개 입력에 최근 최대 5초의 SNR 평균 변화량을 추가한 11→64→64→1 후보별 Double DQN. 미래 정보 없이 연속 가시 구간의 과거만 사용한다.
- 기한 내 수신 비율에 보상, 연속 손실과 핸드오버에 벌점. 기존 보상 가중치 1 / 0.3 / 0.1 유지. Q값 전환 마진 0.02는 dB가 아니다.
- 100개 에피소드로 새로 학습. 평가에는 학습에 사용하지 않은 10개 시드를 쓰고 가중치를 동결했다. 평가 중 탐색 확률은 0이다.

## 10회 평가 요약

| 지표 | 평균 | 표준편차 | 최솟값~최댓값 |
|---|---:|---:|---:|
'''
for metric,label in labels.items():
    s=stats[metric];digits=4 if metric.endswith('pct') else 1
    text+=f'| {label} | {float(s["mean"]):.{digits}f} | {float(s["std"]):.{digits}f} | {float(s["min"]):.{digits}f}~{float(s["max"]):.{digits}f} |\n'
text+='\n![10회 평가 결과](evaluation.png)\n\n## 각 회차 결과\n\n| 회차 | 손실률 % | 기한 내 도착률 % | 최대 연속 손실 개 | 핸드오버 회 |\n|---|---:|---:|---:|---:|\n'
for r in runs:text+=f'| {r["repeat"]} | {float(r["loss_pct"]):.4f} | {float(r["onTime_pct"]):.4f} | {r["maxLossRun"]} | {r["handovers"]} |\n'
phy=sum(int(r['phyLoss']) for r in runs);ho=sum(int(r['handoverLoss']) for r in runs)
text+=f'\n전체 평가 360,000개 중 {sum(int(r["lost"]) for r in runs):,}개 손실: PHY {phy:,}개, 핸드오버 {ho:,}개, 연결 불가 0개. 이번 결과에서는 손실의 약 {100*ho/(phy+ho):.1f}%가 핸드오버 중단에서 발생했다. 기한 초과 도착과 미확정 패킷은 모두 0개다.\n'
text+='''
## 해석 범위

이번 결과는 한 번 학습한 모델을 서로 다른 10개 테스트 시드에서 평가한 값이다. 학습 초기화를 10번 반복한 실험은 아니다. 100회 학습을 마쳤다는 사실만으로 수렴이나 최적성을 주장할 수 없다.

기존 42.8472%는 고도각 선택·4° 전환 마진의 다른 단일 실행 결과다. 같은 평가 시드로 기준 정책을 다시 실행하기 전까지 직접적인 개선율이나 DDQN 우수성을 결론 내리지 않는다. 다음 비교 때는 동일한 PHY·위성 움직임·채널 시드·패킷 난수를 맞춘다.

`summary.csv`의 95% 구간은 테스트 시드 평균의 근사 t 구간이다. 신경망 초기화 차이, PHY 표의 유한 표본 오차, 실제 기상 모델의 불확실성은 포함하지 않는다.

## 저장 파일과 실행

MATLAB에서 상위 `gsl` 폴더의 `main_gsl_ddqn_6x11.m`을 실행하면 저장된 10회 결과와 후보 표·패킷 재생 화면을 연다. 회차 선택 메뉴로 각 평가를 확인한다.

- `training.csv`, `agent.mat`: 100회 연습 기록과 마지막 학습 모델.
- `runs.csv`, `summary.csv`: 평가 10회 성적과 요약.
- `repeat_01`~`repeat_10`: 각 36,000개 전체 패킷, 연속 손실 구간, 위성 선택, 후보 SNR, ISL 입력, 재생 자료.
- `full_verification.json`: 전체 360,000개 패킷의 번호·손실 원인·기한·연속 손실·ISL 입력 대조.

![후보 표와 신호](candidate_dashboard.png)

![패킷 재생](packet_viewer.png)
'''
(root/'RESULTS.md').write_text(text,encoding='utf8')
print(text.split('## 각 회차 결과')[0])
