import csv,json,math,statistics as st
from pathlib import Path
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def average(rows,k):return st.fmean(float(r[k]) for r in rows)
metrics=['loss_pct','maxLossRun','onTime_pct','handovers']
result={'method':'TD-prioritized replay pilot; reward unchanged','trainingEpisodesPerMethod':100,'originalPairedEvaluation':{},'newPairedValidation':{},'trainingCoverage':{},'QRealizedReturnDiagnostics':{}}
for mode in ['uniform','prioritized']:
    base=root/f'results_{mode}';out=base/(base/'latest_result.txt').read_text().strip()
    runs=read(out/'runs.csv');assert len(runs)==10
    result['originalPairedEvaluation'][mode]={k:average(runs,k) for k in metrics}
    cov=read(out/'replay_coverage.csv');result['trainingCoverage'][mode]=cov
    assert sum(int(r['seenTransitions']) for r in cov)==60000
    fresh=[r for r in read(root/'validation_new_seeds'/'runs.csv') if r['mode']==mode]
    assert len(fresh)==10
    result['newPairedValidation'][mode]={k:average(fresh,k) for k in metrics}
    trace=[r for r in read(root/'validation_new_seeds'/'Q_return_traces.csv') if r['mode']==mode]
    # Censor final 120 s for diagnostics of a time-agnostic Q function.
    core=[r for r in trace if float(r['time_s'])<480]
    high=[r for r in core if float(r['PER'])>=.9]
    result['QRealizedReturnDiagnostics'][mode]={
        'scope':'on-policy sampled return residual, NOT exact expected Q error; final 120s excluded',
        'meanAbsResidual':st.fmean(abs(float(r['QminusRealizedReturn'])) for r in core),
        'highPERsampleCount':len(high),
        'highPERmeanAbsResidual':st.fmean(abs(float(r['QminusRealizedReturn'])) for r in high) if high else None,
        'unitPERChoicesWithNonunitAlternative':sum(float(r['PER'])==1 and float(r['bestAvailablePER'])<1 for r in trace)}
paired=[]
for label,source in [('original',result['originalPairedEvaluation']),('new',result['newPairedValidation'])]:
    if label=='original':
        tables={}
        for mode in ['uniform','prioritized']:
            base=root/f'results_{mode}';out=base/(base/'latest_result.txt').read_text().strip();tables[mode]=read(out/'runs.csv')
    else:
        rows=read(root/'validation_new_seeds'/'runs.csv');tables={mode:[r for r in rows if r['mode']==mode] for mode in ['uniform','prioritized']}
    for k in metrics:
        assert [r['seed'] for r in tables['uniform']]==[r['seed'] for r in tables['prioritized']]
        d=[float(b[k])-float(a[k]) for a,b in zip(tables['uniform'],tables['prioritized'])]
        mean=st.fmean(d);half=2.26215716274099*st.stdev(d)/math.sqrt(10)
        paired.append({'cohort':label,'metric':k,'prioritizedMinusUniform':mean,'lower95':mean-half,'upper95':mean+half})
result['pairedDifferences']=paired
(root/'comparison_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
with (root/'paired_differences.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
text=['Q점수 학습 보완 실험 결과','',
'보상식, 위성군, 감쇠, PHY, 신경망, 학습 횟수와 탐색 비율은 유지하고 경험을 복습하는 방식만 변경함.',
'Q점수나 실제 오류확률을 수동으로 보정하지 않음. 두 방식 각각 100회 학습함.',
'기존 방식: 경험을 같은 확률로 추출. 수정 방식: TD 오차가 큰 경험을 더 자주 추출하고 중요도 가중치로 편향을 보정.',
'방법 근거: Schaul et al., Prioritized Experience Replay, https://arxiv.org/abs/1511.05952','']
for label,key in [('기존 진단에 사용한 10개 시드','originalPairedEvaluation'),('새로운 검증 시드 10개 (20274001~20274010)','newPairedValidation')]:
    text.append(label)
    for mode in ['uniform','prioritized']:
        a=result[key][mode];text.append(f"{mode}: 손실률 {a['loss_pct']:.4f}%, 최대 연속 손실 평균 {a['maxLossRun']:.1f}개, 기한 내 도착률 {a['onTime_pct']:.4f}%, 핸드오버 {a['handovers']:.1f}회")
    text.append('')
text+=['학습 데이터 확인']
for mode,cov in result['trainingCoverage'].items():
    high=next(r for r in cov if r['regime']=='PER_ge_0.9');text.append(f"{mode}: 오류확률 90% 이상 경험 {high['seenTransitions']}/60000, 학습 배치에서 복습된 횟수 {high['sampledTransitions']} (중복 포함)")
text+=['','주의: TD 오차와 실제 기대 Q값의 오차는 같지 않음. 기록된 누적 보상과 Q값의 차이는 관측 표본 기반 진단임.',
'행동이 달라지면 방문 상태도 달라지므로 두 방식의 Q 잔차를 완전히 동일한 입력에서의 오차로 볼 수 없음.',
'각 방식의 학습 초기화는 1개만 사용했으므로 다양한 학습 시드에서의 재현성은 별도 검증이 필요함.',
'1000회 모델과 비교할 경우 학습량이 다르므로 이번 수정 효과는 100회 균일 복습 대조군과 비교해야 함.',
'기존 보상식과 저장된 원본 모델은 변경하지 않음.']
(root/'실험결과.txt').write_text('\n'.join(text),encoding='utf-8-sig')
print(json.dumps(result,indent=2))
