import csv,json,math,hashlib
from pathlib import Path
root=Path(__file__).parent;out=root/'full_episode_audit'
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
pairs=read(out/'full_episode_pairs.csv');scores=read(out/'fixed_trajectory_rescoring.csv');assert len(pairs)==92
def analyze(deltas):
    counts={'cases':92,'preferLongerFullMax':0,'preferMoreFullLoss':0,'dominatedOnLossAndMax':0,'preferStay':0,'preferSwitch':0,'ties':0}
    details=[]
    for r,d in zip(pairs,deltas):
        if abs(d)<=1e-9:counts['ties']+=1;continue
        preferred='switch' if d>0 else 'stay';other='stay' if d>0 else 'switch'
        counts['preferSwitch' if d>0 else 'preferStay']+=1
        loss=int(r[preferred+'FullLoss'])-int(r[other+'FullLoss'])
        burst=int(r[preferred+'FullMaxRun'])-int(r[other+'FullMaxRun'])
        counts['preferMoreFullLoss']+=loss>0;counts['preferLongerFullMax']+=burst>0
        counts['dominatedOnLossAndMax']+=loss>=0 and burst>=0 and (loss>0 or burst>0)
        if burst>0:details.append({**r,'preferred':preferred,'extraMaxRun':burst,'extraLoss':loss})
    return counts,details
result={'scope':'92 correlated training-state pairs from 49 seeds, full 600-second episode metrics; fixed parent policy after first action','weights':{'onTime':1,'burst':.3,'handover':.1},'gamma':.95,'rescoring':{}}
for name in dict.fromkeys(r['scoring'] for r in scores):
    values={(r['seed'],r['time_s']):float(r['switchMinusStay']) for r in scores if r['scoring']==name}
    stats,details=analyze([values[r['seed'],r['time_s']] for r in pairs]);result['rescoring'][name]=stats
    if name=='original':
        with (out/'full_max_conflicts.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(details)
assert result['rescoring']['onTime_only_no_discount']['preferMoreFullLoss']==0
result['capActiveInTheseEpisodes']=max(int(r[k]) for r in pairs for k in ['stayFullMaxRun','switchFullMaxRun'])>600
example=next(r for r in pairs if r['seed']=='20269137' and int(r['time_s'])==599);result['example']=example
result['discountWeights']={str(k):.95**k for k in [10,20,30,60]}
result['syntheticFormulaCounterexample']=read(root/'synthetic_formula_counterexample.csv')
result['handoverExtraCostInSuccessfulPacketUnits']=.1*60
result['runExtraPenaltiesNoDiscount']={str(n):.3*sum(min(k,600) for k in range(1,n+1))/3600 for n in [6,20,48,60]}
manifest=json.loads(Path('work/gsl-stay-switch-1126/experiment_manifest.json').read_text())
for p,h in manifest['preservedSHA256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
result['originalRewardAndModelsUnchanged']=True
result['rescoringCaveat']='Same trajectories only. Scores do not predict behavior or performance after retraining with changed weights.'
(root/'alignment_summary.json').write_text(json.dumps(result,indent=2),encoding='utf8')
with (root/'rescoring_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    rows=[{'scoring':k,**v} for k,v in result['rescoring'].items()];w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
text=['현재 GSL 보상과 패킷 손실 목표의 일치 여부 점검','',
'결론: 손실을 줄이는 방향은 반영돼 있지만, 600초 동안의 최대 연속 손실을 직접 최소화하는 식과는 다름. 계산 오류와 목표 불일치는 구분해야 함.',
'보상/가중치/학습 모델은 수정하지 않았으며 재학습도 하지 않음.','',
'현재 1초 보상 = 기한 내 수신 비율 - 0.3 × 해당 60개 패킷의 연속 손실 비용 평균 - 0.1 × 핸드오버 여부.',
'연속 손실 비용은 각 패킷에서 min(현재 이어진 손실 길이/60, 10). 따라서 전체 손실 길이 합의 영향도 받고 에피소드 최대값 자체는 아님.',
'초기 연속 손실 0, 벌점 상한에 닿지 않은 하나의 손실 구간 길이가 L이면, 그 구간의 추가 벌점 합은 0.3*L*(L+1)/(2*3600). 여러 구간이면 이 값을 모두 더함.',
'설명용 합성 패킷 예: 같은 1초, 두 경우 모두 60개 중 40개 손실, 핸드오버 없음.',
'A: 20개 연속 손실 1회 + 1개 손실 20회. 최대 20개, 보상 0.3141667.',
'B: 14개 + 13개 + 13개 손실. 최대 14개, 보상 0.3094167.',
'A는 최대 연속 손실이 더 크지만 보상은 더 높음. 이 비교는 실제 GSL 실험 결과가 아니라 공식 성질을 확인한 합성 예시임.',
'가중치 0.3만 키워도 위 두 경우의 순위는 바뀌지 않음. 최대값과 누적 비용의 정의 차이임.','',
'실제 시뮬레이션 재현: 유지/전환 92쌍을 600초 전체로 확장. 같은 현재 상태, 위치, 채널, 패킷 난수 및 같은 고정 후속 정책을 사용.',
'각 1초 보상을 수신/연속 손실/핸드오버 항으로 독립 재계산해 원래 보상과 일치함을 검증. 앞선 60초 구간 보상도 정확히 재현.',
'이전에 확인한 13개는 최대 60초 구간에서의 충돌 수치. 600초 전체 최대 연속 손실로 재확인하면 8개.',
'전체 손실이 더 많은 선택에 보상이 높았던 경우는 12개. 전체 손실과 최대 연속 손실 두 기준에서 열세인 선택을 보상이 선호한 경우는 10개.',
'이 수치는 고정된 정책/학습 시드 사례의 기술통계. 인접한 시점이 포함돼 92개 독립 반복으로 간주하면 안 됨.','',
'명확한 실제 사례: 학습 시드 20269137, 마지막 599초 선택.',
'유지: 전체 손실 1239개, 최대 연속 손실 62개, 마지막 1초 보상 -0.1625000.',
'전환: 전체 손실 1238개, 최대 연속 손실 36개, 마지막 1초 보상 -0.1656667.',
'전환의 수신 항 개선 +0.0166667, 연속 손실 항 개선 +0.0801667, 추가 핸드오버 벌점 -0.1.',
'합계 -0.0031667이므로 손실 1개 및 최대 연속 손실 26개를 줄여도 현재 보상은 유지를 선호함.',
'이는 별도 핸드오버 억제 비용을 둔 결과로, 수치 계산 오류라고 할 수는 없음.','',
'같은 경로를 다른 점수로 재계산한 진단(새 정책 학습 결과가 아님):',
'원래 보상: 최대 연속 손실과 순위 충돌 8개.',
'추가 핸드오버 항만 제외: 충돌 1개.',
'할인만 제외: 충돌 8개.',
'연속 손실 항을 제외: 충돌 20개. 연속 손실 항 자체를 없애는 방향도 적절하지 않음.',
'현재 할인율 0.95에서는 지금 선택을 평가할 때 30초 뒤 보상은 약 21.5%, 60초 뒤는 약 4.6% 가중치임.',
'현재 비교 사례들의 최대 연속 손실은 600개 미만이므로, 600개에서 시작하는 벌점 상한은 이번 충돌의 원인이 아님.','',
'해석: Q값이 현재 보상을 정확히 학습하더라도 최대 연속 손실이 반드시 최소가 되는 것은 아님.',
'연구 우선순위가 최대 연속 손실 감소라면 최대 길이/증가량을 직접 반영하는 항과 추가 핸드오버 비용의 우선순위를 별도로 설계·검증할 필요가 있음.',
'보상을 바꿔 재학습했을 때의 성능은 아직 검증하지 않았음. 이번 작업은 점검만 수행함.']
(root/'보상점검결과.txt').write_text('\n'.join(text),encoding='utf-8-sig')
print(json.dumps(result,indent=2))
