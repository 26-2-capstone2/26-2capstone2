from pathlib import Path
import csv
root=Path('C:/Users/succe/Desktop/codex/1128/hold_diagnostic_1128/results')
def read(name):
    with (root/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
summary=read('episode_summary.csv');local=read('switch_summary.csv');pairs=read('switch_pairs.csv')
lines=['강제 유지 vs DDQN 진단 결과','기존 정적 격자, 6dB, 재학습 없음. 3600km 공통 영역 실험이 아님.','',
'A. 전체 600초: 양쪽의 첫 선택은 같고, 유지 방식은 그 위성을 끝까지 유지한다.',
'각 위성군 10회 평균. 연속 손실 평균 길이/횟수는 2개 이상 구간만 집계.']
for grid in ['6x11','20x20','36x36']:
    lines.append(grid)
    for policy in ['hold_initial','DDQN']:
        a={r['metric']:float(r['mean']) for r in summary if r['grid']==grid and r['policy']==policy}
        lines.append(f"  {policy}: 손실률 {a['loss_pct']:.3f}%, 평균 연속 길이 {a['meanLength_ge2']:.3f}개, 최대 연속 길이 {a['maxLength']:.1f}개, 연속 구간 {a['burstCount_ge2']:.1f}회, 핸드오버 {a['handovers']:.1f}회")
lines+=['','B. 각 전환 시점: 원래 DDQN 전환 vs 현재 위성을 1초 유지하고 이후 DDQN으로 복귀.',
'같은 시점부터 다음 10초의 최대 연속 손실을 비교하며 직전 연속 손실을 포함한다.',
'끝까지 10초가 남지 않은 전환은 제외. 창 끝의 손실이 이어지는 경우 오른쪽 검열을 표시한다.']
for r in local:
    n=int(r['switchProbes']);better=int(r['DDQN_shorter']);same=int(r['equalPeak']);worse=int(r['DDQN_longer'])
    lines.append(f"{r['grid']}: {n}개 시점 중 DDQN이 더 짧음 {better}({100*better/n:.1f}%), 같음 {same}({100*same/n:.1f}%), 더 김 {worse}({100*worse/n:.1f}%).")
    lines.append(f"  창 안 최대 길이 평균: DDQN {float(r['DDQN_meanPeak_10s']):.2f}개 vs 1초 유지 {float(r['hold_meanPeak_10s']):.2f}개.")
    lines.append(f"  유지하면 12개 이상/전환하면 12개 미만: {r['DDQN_averted_ge12']}개 시점; 반대: {r['DDQN_created_ge12']}개 시점.")
lines+=['','해석상 제한:',
'전체 유지 대조군은 전혀 적응하지 않는 진단용 정책으로, 이를 이겼다고 최고 SNR보다 우수하다는 증거가 되지 않는다.',
'전환 시점 분석은 해당 상태/모델/미래 SNR/공유 난수에 조건부인 단일 개입 결과다.',
'10초 창이 겹치므로 시점들은 독립 표본이 아니다. 시점 수를 독립 실험 수나 유의확률로 해석하지 않는다.',
'10초의 최대 길이는 전체 600초 최대 길이가 아니다. 미래를 본 결과는 학습이나 행동 선택에 넣지 않았다.',
'핸드오버의 6개 손실도 포함. 신경망을 재학습하거나 PHY 곡선을 조정하지 않았다.']
(root/'결과해석.txt').write_text('\n'.join(lines),encoding='utf8')
print('\n'.join(lines))
