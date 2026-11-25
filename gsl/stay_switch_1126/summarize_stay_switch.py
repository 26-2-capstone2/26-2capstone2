import csv,json,math,hashlib,statistics as st
from pathlib import Path
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
base=root/'results_paired';out=base/(base/'latest_result.txt').read_text().strip()
parent=Path('C:/Users/succe/Desktop/codex/1123/gsl/q_context_1126/results_context/20261126_003447_332')
old=read(parent/'runs.csv');new=read(out/'runs.csv');fresh=read(root/'validation_new_seeds'/'runs.csv')
metrics=['loss_pct','maxLossRun','onTime_pct','handovers']
summary={'trainingEpisodesPerMethod':100,'control':'12-input context model with ordinary replay',
 'change':'paired stay/switch simulator transitions and 8/64 rare replay quota','original10':{},'fresh10':{},'pairedDifferences':[]}
for label,tables in [('original10',{'context':old,'paired':new}),('fresh10',{m:[r for r in fresh if r['mode']==m] for m in ['context','paired']})]:
    assert all(len(t)==10 for t in tables.values())
    assert [r['seed'] for r in tables['context']]==[r['seed'] for r in tables['paired']]
    for mode,rows in tables.items():
        summary[label][mode]={k:st.fmean(float(r[k]) for r in rows) for k in metrics}
        summary[label][mode]['worstRunAcrossTen']=max(int(r['maxLossRun']) for r in rows)
        summary[label][mode]['meanPHYloss']=st.fmean(int(r['phyLoss']) for r in rows)
        summary[label][mode]['meanHOloss']=st.fmean(int(r['handoverLoss']) for r in rows)
    for k in metrics:
        d=[float(b[k])-float(a[k]) for a,b in zip(tables['context'],tables['paired'])]
        mean=st.fmean(d);half=2.26215716274099*st.stdev(d)/math.sqrt(10)
        summary['pairedDifferences'].append({'cohort':label,'metric':k,'pairedMinusParent':mean,'lower95':mean-half,'upper95':mean+half})
trace=read(root/'validation_new_seeds'/'Q_return_traces.csv');summary['QDiagnostics']={}
for mode in ['context','paired']:
    rows=[r for r in trace if r['mode']==mode];core=[r for r in rows if float(r['time_s'])<480]
    summary['QDiagnostics'][mode]={'sampledReturnNotExactExpectedQ':True,
        'meanAbsRealizedReturnResidual':st.fmean(abs(float(r['QminusRealizedReturn'])) for r in core),
        'unitPERWithBetterAlternative':sum(float(r['PER'])==1 and float(r['bestAvailablePER'])<1 for r in rows)}
pairs=read(out/'training_pairs.csv');counter=read(out/'replay_counts.csv')[-1]
assert int(counter['rareTransitions'])==2*len(pairs)
assert int(counter['rareSamplesUsed'])+int(counter['normalSamplesUsed'])==int(counter['updates'])*64==7437*64
summary['trainingReplay']={'primaryTransitions':60000,'pairedCases':len(pairs),'extraSimulatorTransitions':2*len(pairs),**counter}
summary['staySwitchDiagnostic']=json.loads((root/'diagnostic_summary.json').read_text())
manifest=json.loads((root/'experiment_manifest.json').read_text())
for p,h in manifest['preservedSHA256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
summary['parentAndRewardUnchanged']=True
(root/'comparison_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
with (root/'paired_differences.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=summary['pairedDifferences'][0].keys());w.writeheader();w.writerows(summary['pairedDifferences'])
text=['모두 나쁜 구간의 유지/전환 비교와 짝 경험 학습','',
'비교 방법: 가시 후보의 모델상 성공률이 모두 10% 미만인 시점에서, 첫 1초를 현재 위성 유지/현재 위성을 제외한 최고 SNR 후보로 전환으로 나눔.',
'이후는 같은 고정된 12입력 DDQN 정책을 따르게 하고 최대 60초 동안 비교. 마지막 60초 안에 시작한 사례는 시뮬레이션 끝까지만 비교.',
'진단은 학습 시드에만 적용. 유지 가능한 현재 위성이 없는 3개 시점을 제외한 92개 시점을 비교함. 서로 인접한 시점이 있어 독립된 92회 실험은 아님.',
'현재 보상 기준: 유지 우세 54개, 전환 우세 38개.',
'구간 총 손실 패킷 수 기준: 유지가 적음 29개, 전환이 적음 48개, 동일 15개.',
'구간 최대 연속 손실 기준(기존 진행 중 손실 길이 포함): 유지가 작음 20개, 전환이 작음 41개, 동일 31개.',
'무조건 유지가 정답이 아님. 보상 선호와 패킷 손실 선호가 항상 같지는 않음. 결과는 같은 미래 채널 실현값 및 후속 정책에 조건부인 분석임.','',
'학습 변경: 위 두 행동의 1초 보상 및 다음 상태를 시뮬레이터에서 얻어 별도 버퍼에 저장. 64개 배치 중 최대 8개를 이 버퍼에서 복습.',
'60초 미래 결과나 승자 라벨은 학습에 넣지 않음. 보상, PHY, 12개 입력, 신경망, 6dB, 6x11, 100회 기본 학습과 총 업데이트 수는 유지.',
'물리 오류율 또는 행동 선택을 수동으로 보정하지 않으며, 평가 때 분기/학습/강제 유지 규칙은 사용하지 않음.',
f'기본 결정 60000개 외에 시뮬레이터 분기 전이 {2*len(pairs)}개를 추가함. 따라서 환경 조회 수까지 완전히 같은 실험은 아님.',
'희귀 버퍼 비중은 학습 상태의 가중치를 의도적으로 바꾼 것임. 중요도 역보정은 적용하지 않음.','']
for label,title in [('original10','기존 10개 평가 시드'),('fresh10','새 검증 시드 10개: 20276001~20276010')]:
    text.append(title)
    for m,r in summary[label].items():text.append(f"{m}: 손실률 {r['loss_pct']:.4f}%, 최대 연속 손실 평균 {r['maxLossRun']:.1f}개, 기한 내 도착률 {r['onTime_pct']:.4f}%, 핸드오버 {r['handovers']:.1f}회. 최악 연속 손실 {r['worstRunAcrossTen']}개.")
    text.append('')
text+=['한계: 학습 초기화는 한 개이므로 다양한 학습 시드에서의 재현성은 별도 확인이 필요함.',
'이 비교의 대조군은 직전 12입력 모델임. 최초 11입력 또는 1000회 모델과 혼동하지 말 것.',
'현재 보상은 수신/연속 손실/핸드오버를 함께 평가하므로 단일 패킷 지표와 완전히 일치하지 않을 수 있음.',
'원래 모델 및 보상 파일은 유지됨. main_gsl_stay_switch 실행 시 재학습 없이 결과를 볼 수 있음.']
(root/'실험결과.txt').write_text('\n'.join(text),encoding='utf-8-sig')
print(json.dumps(summary,indent=2))
