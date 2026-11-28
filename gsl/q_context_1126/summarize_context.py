import csv,json,math,hashlib,statistics as st
from pathlib import Path
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
base=root/'results_context';out=base/(base/'latest_result.txt').read_text().strip()
reference=Path('C:/Users/succe/Desktop/codex/1123/gsl/ddqn_6x11/results_ddqn_6x11/20261123_160855_135')
old=read(reference/'runs.csv');new=read(out/'runs.csv');fresh=read(root/'validation_new_seeds'/'runs.csv')
metrics=['loss_pct','maxLossRun','onTime_pct','handovers']
summary={'trainingEpisodes':100,'change':'one additional candidate-set context input; original reward and uniform replay','original10':{},'fresh10':{},'pairedDifferences':[],'QReturnDiagnostics':{}}
for label,tables in [('original10',{'uniform':old,'context':new}),('fresh10',{m:[r for r in fresh if r['mode']==m] for m in ['uniform','context']})]:
    assert all(len(t)==10 for t in tables.values())
    assert [r['seed'] for r in tables['uniform']]==[r['seed'] for r in tables['context']]
    for mode,rows in tables.items():
        summary[label][mode]={k:st.fmean(float(r[k]) for r in rows) for k in metrics}
        summary[label][mode]['worstRunAcrossTen']=max(int(r['maxLossRun']) for r in rows)
    for k in metrics:
        d=[float(b[k])-float(a[k]) for a,b in zip(tables['uniform'],tables['context'])]
        mean=st.fmean(d);half=2.26215716274099*st.stdev(d)/math.sqrt(10)
        summary['pairedDifferences'].append({'cohort':label,'metric':k,'contextMinusOriginal':mean,'lower95':mean-half,'upper95':mean+half})
trace=read(root/'validation_new_seeds'/'Q_return_traces.csv')
for mode in ['uniform','context']:
    rows=[r for r in trace if r['mode']==mode];core=[r for r in rows if float(r['time_s'])<480]
    high=[r for r in core if float(r['PER'])>=.9]
    summary['QReturnDiagnostics'][mode]={'sampledReturnNotExactExpectedQ':True,
        'maeExcludingFinal120s':st.fmean(abs(float(r['QminusRealizedReturn'])) for r in core),
        'highPERsamples':len(high),
        'highPERmae':st.fmean(abs(float(r['QminusRealizedReturn'])) for r in high) if high else None,
        'unitPERChoicesWithBetterAlternative':sum(float(r['PER'])==1 and float(r['bestAvailablePER'])<1 for r in rows)}
manifest=json.loads((root/'audit_and_experiment.json').read_text())
for p,h in manifest['preservedSHA256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
summary['originalFilesUnchanged']=True
census=read(root/'training_candidate_context_census.csv')
counts={k:sum(int(r[k]) for r in census) for k in list(census[0])[1:]}
assert sum(counts.values())==60000
summary['trainingCandidateSetCensus']=counts
(root/'comparison_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
with (root/'paired_differences.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=summary['pairedDifferences'][0].keys());w.writeheader();w.writerows(summary['pairedDifferences'])
text=['Q 목표값 및 후보 비교 구조 점검','',
'계산 점검: 보상 + 할인율 × 다음 온라인 네트워크가 고른 후보의 타깃 Q값을 사용하고 있음. 종료/후보 없음에서는 다음 Q를 더하지 않음. 산술 오류는 확인되지 않음.',
'실제 선택에는 Q 여유값 0.02가 있지만 학습 목표는 순수 최대 Q를 사용함. 두 방식 차이는 1회 백업에서 최대 0.019. 이 수치를 누적 학습 오차의 상한으로 볼 수는 없음.',
'입력 구조 점검: 한 후보의 기존 입력이 같으면, 다른 비연결 후보의 신호가 달라져도 그 후보 점수는 그대로임. 구조적인 정보 누락 가능성이지 실제 실패의 유일한 원인이라는 증명은 아님.',
'이번 변경: 모든 현재 가시 후보 중 가장 높은 예상 수신 성공률 1개를 추가함. 입력 11개에서 12개로 변경.',
'초기 기존 가중치는 복사하고 추가 입력 가중치만 0으로 설정해 시작 점수를 맞춤.',
'보상, PHY, 감쇠 6dB, 6x11 위성군, 균일 경험 재생, 학습 시드와 탐색 비율은 유지. 앞선 우선 경험 재생은 사용하지 않음.',
'기존 100회 모델과 추가 입력 모델을 비교함. 1000회 모델과의 학습량 동일 비교는 아님.','']
for label,title in [('original10','기존 10개 평가 시드'),('fresh10','새 검증 시드 10개: 20275001~20275010')]:
    text.append(title)
    for m,r in summary[label].items():text.append(f"{m}: 손실률 {r['loss_pct']:.4f}%, 최대 연속 손실 평균 {r['maxLossRun']:.1f}개, 기한 내 도착률 {r['onTime_pct']:.4f}%, 핸드오버 {r['handovers']:.1f}회. 10회 전체에서 가장 긴 손실은 {r['worstRunAcrossTen']}개.")
    text.append('')
text+=['한계: 학습 초기화는 1개이며, 여러 학습 시드에서의 안정성은 확인하지 않음.',
'Q값과 기록된 누적 보상의 차이는 표본 기반 진단이며 정확한 기대 Q 오차는 아님.',
'남은 시간 정보는 아직 입력에 없고, 최고 성공률 1개만으로 후보 전체 상태를 완전히 표현하지는 못함.',
'원래 모델/보상/환경 파일의 해시는 변경 전과 동일함.',
'main_gsl_q_context 실행 시 재학습 없이 저장된 비교와 패킷 결과가 열림.']
critical=counts['allCandidatesPER1_seconds']+counts['bestSuccess0to0_1_seconds']
text+=['',f'학습 상황 분포: 가장 좋은 후보도 성공률 10% 미만인 시점은 {critical}/60000 ({100*critical/60000:.4f}%).',
       f"모든 후보의 모델 PER가 1인 시점은 {counts['allCandidatesPER1_seconds']}/60000.",
       '이는 환경의 모든 가시 후보를 센 통계로, 정책이 선택한 나쁜 위성의 비율과는 다름.',
       '후보 전체가 나쁜 상황의 표본이 적다는 사실은 확인했으나, 이것이 실패의 유일한 원인이라는 인과 증명은 아님.']
(root/'실험결과.txt').write_text('\n'.join(text),encoding='utf-8-sig')
print(json.dumps(summary,indent=2))
