import csv,sys
from pathlib import Path
out=Path(sys.argv[1])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
base=read(out/'baseline_runs.csv');maximum=read(out/'maxsnr_runs.csv');ddqn=read(out/'ddqn_runs.csv')
mean=lambda data,key:sum(float(r[key]) for r in data)/len(data)
text='''# 고도각 / 최대 SNR / DDQN — 동일 조건 10회 비교

최대 SNR 방식은 **학습 없이 매초 가장 높은 SNR의 가시 위성 하나를 선택**했다. 전환 마진은 없다. 실제 전환에는 동일한 100 ms 중단을 적용했다. 기존 고도각 방식과 DDQN의 완료된 평가 결과를 재사용했으며 재학습하지 않았다.

세 정책 모두 6×11, 감쇠 6 dB, 600초, 60 pps·160 B, 기한 20 ms, 같은 툴박스 PHY 표다. 시드 20269301~20269310에서 위성 좌표·전체 후보 SNR·원본 패킷별 오류 난수를 맞췄다. 범위는 지상국→첫 수신 위성까지다.

## 10회 평균

| 지표 | 기존 고도각+4° | 최대 SNR | DDQN+Q 마진 0.02 |
|---|---:|---:|---:|
'''
for key,label in [('loss_pct','손실률 %'),('onTime_pct','기한 내 도착률 %'),('maxLossRun','회차별 최대 연속 손실 개'),('handovers','핸드오버 회')]:
    digits=4 if key.endswith('pct') else 1
    text+=f'| {label} | {mean(base,key):.{digits}f} | {mean(maximum,key):.{digits}f} | {mean(ddqn,key):.{digits}f} |\n'
text+='''
![세 정책 평균과 표본 표준편차](three_policy_means.png)

## 핵심 해석

1. **단순 최대 SNR 규칙만으로도 손실률이 42.5797%→6.0467%로 낮아졌다.** 고도각 방식 대비 큰 격차 전체를 DDQN 학습 효과로 해석하면 안 된다.
2. 최대 SNR 대비 DDQN 손실률은 **6.0467%→4.0942%, 1.9525%p 감소**(상대 약 32.29%)했다. 기한 내 도착률도 같은 폭으로 높아졌다.
3. 핸드오버는 최대 SNR **269회→DDQN 131회**, 평균 138회(약 51.30%) 줄었다.
4. **최대 연속 손실 평균은 최대 SNR 56개, DDQN 64.3개**다. 최대 SNR보다 연속 손실까지 좋아졌다고 할 수 없다. 같은 시드별 차이의 평균에 대한 근사 95% t 구간은 -3.04~19.64개로 0을 포함한다.

고도각 방식과 비교했을 때는 DDQN이 훨씬 좋았지만, 신호를 직접 고려하는 단순 기준을 추가하면 차이는 작아진다. 이번 DDQN 정책의 장점은 순수 최대 SNR보다 전체 손실과 전환을 줄인 점이고, 연속 손실 최소화는 보완 과제로 남는다.

## 최대 SNR 대비 손실 원인 — 평가 10회 합계

| 원인 | 최대 SNR | DDQN |
|---|---:|---:|
'''
for key,label in [('phyLoss','PHY 오류'),('handoverLoss','핸드오버'),('outageLoss','연결 불가'),('lost','전체 손실')]:
    text+=f'| {label} | {sum(int(r[key]) for r in maximum):,} | {sum(int(r[key]) for r in ddqn):,} |\n'
text+='''
DDQN은 PHY 오류가 더 많았지만 핸드오버 손실을 더 크게 줄여 전체 손실이 감소했다. 결과에 맞춰 PHY 값이나 전력을 수정하지 않았다.

## 같은 시드의 10회 결과

| 회차 | 최대 SNR 손실률 % | DDQN 손실률 % | 최대 SNR 연속 손실 | DDQN 연속 손실 | 최대 SNR HO | DDQN HO |
|---|---:|---:|---:|---:|---:|---:|
'''
for a,b in zip(maximum,ddqn):
    text+=f'| {a["repeat"]} | {float(a["loss_pct"]):.4f} | {float(b["loss_pct"]):.4f} | {a["maxLossRun"]} | {b["maxLossRun"]} | {a["handovers"]} | {b["handovers"]} |\n'
text+='''
![최대 SNR과 DDQN의 회차별 비교](maxsnr_vs_ddqn.png)

## 한계와 다음 확인

DDQN에는 Q값 전환 마진 0.02가 있고 최대 SNR에는 전환 마진이 없다. 따라서 차이를 전부 신경망 학습만의 효과로 분리할 수 없다. 다음에는 같은 시드의 최대 SNR+히스테리시스와 비교하거나 DDQN 전환 마진을 제거한 실험으로 나눠 보는 것이 필요하다.

이번 통계는 한 번 학습한 모델과 지정한 PHY·채널 가정에 대한 10개 테스트 시드의 결과다. 다른 학습 초기화·실제 기상·실제 장비까지 일반화한 증거가 아니다. 학습 보상에 연속 손실 벌점이 들어 있어도 모든 지표가 자동으로 개선되지는 않는다.

## 실행과 파일

상위 `gsl` 폴더에서 `main_gsl_compare_maxsnr` 실행. 저장 그래프를 연다. `'run'` 인수를 주면 최대 SNR만 10회 재계산한다. 기존 방식과 DDQN의 로컬 평가 자료가 필요하다.

`three_policy_summary.csv`는 세 정책 요약, `all_runs.csv`는 총 30회, `ddqn_vs_maxsnr.csv`는 같은 시드 평균 차이와 근사 95% t 구간이다. 각 `repeat_XX` 폴더에 최대 SNR의 36,000개 전체 패킷·연속 손실·선택·재생 자료를 저장했다. `full_verification.json`에서 6,000개 선택이 실제 최고 SNR인지와 전체 36만 패킷 검증을 확인할 수 있다.
'''
(out/'RESULTS.md').write_text(text,encoding='utf8')
print(text.split('## 같은 시드의 10회 결과')[0])
