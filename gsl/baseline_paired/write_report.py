import csv,sys
from pathlib import Path
out=Path(sys.argv[1])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
stats={r['metric']:r for r in read(out/'comparison_summary.csv')}
base=read(out/'baseline_runs.csv');ddqn=read(out/'ddqn_runs.csv')
text='''# 기존 방식 vs DDQN — 동일 조건 10회 평가

기존 방식은 **학습 없이 10회 평가**했다. 기존 고도각 최대 선택·4° 초과 시 전환 규칙을 그대로 사용했다. DDQN은 이미 100회 학습한 모델의 평가 결과 10회를 재사용했으며 재학습하지 않았다.

## 공통 조건과 검증

6×11 위성, 감쇠 6 dB, 600초, 60 pps·160 B(회차당 36,000패킷), 기한 20 ms, 전환 중단 100 ms, 동일한 툴박스 PHY 표다. 범위는 GS→선택된 첫 수신 위성까지다.

DDQN 평가 시드 20269301~20269310을 그대로 사용했다. 저장된 동일 위성 좌표를 사용하고, 모든 후보의 SNR·원본 Packet ID별 오류 난수·동일 PHY 오류율을 대조했다. 달라지는 것은 선택 위성과 정책별 전환 규칙이다. 기존 고도각 마진 4°와 DDQN의 Q값 마진 0.02는 다른 단위이며, 이 규칙을 포함한 전체 정책끼리 비교했다.

## 10회 평균

| 지표 | 기존 고도각 방식 | DDQN | DDQN−기존 |
|---|---:|---:|---:|
'''
labels={'loss_pct':'패킷 손실률 (%)','onTime_pct':'기한 내 도착률 (%)','maxLossRun':'회차별 최대 연속 손실 (개)','handovers':'핸드오버 (회)'}
for k,label in labels.items():
    s=stats[k];digits=4 if k.endswith('pct') else 1
    text+=f'| {label} | {float(s["baseline_mean"]):.{digits}f} | {float(s["ddqn_mean"]):.{digits}f} | {float(s["ddqnMinusBaseline"]):+.{digits}f} |\n'
text+=f'''
- 손실률: **{abs(float(stats['loss_pct']['ddqnMinusBaseline'])):.4f}%p 감소**, 기존 대비 상대적으로 약 {abs(float(stats['loss_pct']['relativeChange_pct'])):.2f}% 감소.
- 최대 연속 손실 평균: **813개 감소**, 약 {abs(float(stats['maxLossRun']['relativeChange_pct'])):.2f}% 감소.
- 기한 내 도착률: **{float(stats['onTime_pct']['ddqnMinusBaseline']):.4f}%p 증가**.
- 핸드오버: **평균 121회 증가(10→131회)**. 모든 지표가 좋아진 결과는 아니다.

최대 연속 손실의 877.3개·64.3개는 각 600초 실행에서 얻은 최댓값 10개의 평균이다. 모든 회차를 통틀어 가장 긴 구간은 기존 {max(int(r['maxLossRun']) for r in base)}개, DDQN {max(int(r['maxLossRun']) for r in ddqn)}개였다.

![10회 평균과 표본 표준편차](comparison_means.png)

## 같은 시드별 결과

| 회차 | 기존 손실률 % | DDQN 손실률 % | 기존 최대 연속 손실 | DDQN 최대 연속 손실 | 기존 HO | DDQN HO |
|---|---:|---:|---:|---:|---:|---:|
'''
for a,b in zip(base,ddqn):
    text+=f'| {a["repeat"]} | {float(a["loss_pct"]):.4f} | {float(b["loss_pct"]):.4f} | {a["maxLossRun"]} | {b["maxLossRun"]} | {a["handovers"]} | {b["handovers"]} |\n'
text+='''
![동일 시드별 정책 비교](comparison.png)

## 해석

이번 동일 조건 10개 테스트에서는 DDQN 정책이 기존 고도각 방식보다 손실률과 연속 손실을 낮추고 기한 내 도착률을 높였다. 다만 위성 전환은 더 잦았다. 따라서 다음에는 전환 횟수와 손실의 균형을 함께 검토한다.

최대 SNR 방식과는 아직 비교하지 않았다. 이번 결과를 근거로 SNR 기반의 단순 규칙보다 강화학습 자체가 우수하다고 결론 내리면 안 된다. 개선이 신호 품질을 고려한 선택에서 온 것인지, 학습된 장기 전략에서 온 것인지는 추가 비교가 필요하다.

`paired_differences.csv`는 동일 시드에서의 차이, `comparison_summary.csv`는 평균 차이의 근사 95% t 구간을 포함한다. 이는 한 번 학습한 모델과 고정된 시뮬레이션·PHY 가정에 대한 10개 테스트 시드의 통계다. 다른 학습 초기화나 실제 채널까지 일반화한 증거는 아니다.

## 실행과 기록

상위 gsl 폴더에서 `main_gsl_compare_baseline` 실행. 저장 결과를 바로 연다. `main_gsl_compare_baseline('run')`은 기존 방식 10회만 재계산한다.

각 `repeat_XX` 폴더에 기준 방식의 전체 36,000개 패킷·연속 손실·위성 선택과 재생용 자료를 저장했다. DDQN 원본은 기존 ddqn_6x11 결과 폴더에서 보존했다. `pairing_checks.csv`와 `full_verification.json`에서 대응 입력·72만 패킷의 계산식 및 연속 손실 검증을 확인할 수 있다.
'''
(out/'RESULTS.md').write_text(text,encoding='utf8')
print(text.split('## 같은 시드별 결과')[0])
