from pathlib import Path
import csv,json,statistics as st,math
root=Path(__file__).parent;out=root/'results'
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
    with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
runs=read(out/'runs.csv');assert len(runs)==100
fields=['loss_pct','maxLossRun','onTime_pct','handovers','undiscountedReward','discountedStartReturn','excessMaxAboveFloor','differentChoicesOnReferenceStates']
summary=[];paired=[];changes=[];windows=[]
ref={int(r['repeat']):r for r in runs if int(r['episode'])==100}
for episode in range(100,1001,100):
    rows=[r for r in runs if int(r['episode'])==episode];assert len(rows)==10
    for field in fields:
        v=[float(r[field]) for r in rows];d=[float(r[field])-float(ref[int(r['repeat'])][field]) for r in rows]
        half=2.26215716274099*st.stdev(d)/math.sqrt(10)
        summary.append(dict(episode=episode,metric=field,mean=st.mean(v),sampleSD=st.stdev(v),minimum=min(v),maximum=max(v)))
        paired.append(dict(episode=episode,metric=field,meanDifferenceVs100=st.mean(d),pairedCI95_lower=st.mean(d)-half,pairedCI95_upper=st.mean(d)+half))
    for r in rows:
        rep=int(r['repeat']);b=ref[rep]
        changes.append(dict(episode=episode,repeat=rep,seed=r['seed'],lossDifference_pctPoint=float(r['loss_pct'])-float(b['loss_pct']),
            maxRunDifference=int(r['maxLossRun'])-int(b['maxLossRun']),handoverDifference=int(r['handovers'])-int(b['handovers']),
            totalRewardDifference=float(r['undiscountedReward'])-float(b['undiscountedReward']),startReturnDifference=float(r['discountedStartReturn'])-float(b['discountedStartReturn'])))
        if episode==100 or int(r['maxLossRun'])<=int(b['maxLossRun']):continue
        a=read(out/f'episode_{episode:04}_repeat_{rep:02}'/'decision_quality.csv')
        z=read(out/f'episode_0100_repeat_{rep:02}'/'decision_quality.csv')
        lo=max(0,math.floor(float(r['maxBurstStart_s']))-3);hi=min(599,math.floor(float(r['maxBurstEnd_s']))+2)
        for t in range(lo,hi+1):
            x=a[t];y=z[t]
            windows.append(dict(episode=episode,repeat=rep,seed=r['seed'],time_s=t,
                currentMaxRun=r['maxLossRun'],reference100MaxRun=b['maxLossRun'],currentChosenSatID=x['chosenSatID'],reference100ChosenSatID=y['chosenSatID'],
                currentChosenPER=x['chosenPER'],reference100ChosenPER=y['chosenPER'],bestPER=x['bestPER'],
                currentQ=x['predictedQ'],currentMarginBlocked=x['blockedByQMargin'],currentIncomingStreak=x['incomingStreak']))
fixed=read(out/'reference_state_scores.csv');fixedSummary=[]
for e in range(100,1001,100):
    rr=[r for r in fixed if int(float(r['episode']))==e];assert len(rr)==6000
    changed=[r for r in rr if r['currentModelSatID']!=r['reference100SatID']]
    fixedSummary.append(dict(episode=e,states=len(rr),changedChoices=len(changed),changedChoice_pct=100*len(changed)/len(rr),
        meanExpectedLossDifference=st.mean(float(r['expectedLossDifference']) for r in rr),
        changedToHigherImmediateExpectedLoss=sum(float(r['expectedLossDifference'])>1e-9 for r in changed),
        changedToLowerImmediateExpectedLoss=sum(float(r['expectedLossDifference'])< -1e-9 for r in changed)))
write('summary.csv',summary);write('paired_differences.csv',paired);write('per_seed_changes.csv',changes);write('fixed_state_summary.csv',fixedSummary)
if windows:write('worsened_burst_windows.csv',windows)
report={'summary':summary,'pairedDifferences':paired,'sameStateChoices':fixedSummary,'modelsFromOneTrainingRun':True,
    'caveats':['evaluation-seed uncertainty only, one training initialization','checkpoint selection on this cohort is validation, not final test','sampled policy return is not ground-truth Q-star']}
(out/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for e in range(100,1001,100):
    d={r['metric']:r['mean'] for r in summary if r['episode']==e}
    print(json.dumps({'episode':e,**d},ensure_ascii=False))
