from pathlib import Path
import csv,json,statistics as st,math
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
    with (root/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
source=root.parent/'gsl-checkpoint-audit-1127/results'
if not source.exists():source=root.parent/'checkpoint_audit_1127/results'
if not source.exists():source=Path('C:/Users/succe/Desktop/codex/1125/GSL_research_1126/gsl/checkpoint_audit_1127/results')
control=[r for r in read(source/'runs.csv') if int(r['episode']) in [100,200]]
allrows=[]
for r in control:r['mode']='control';allrows.append(r)
for mode in ['low_lr','large_buffer','soft_target']:
    rr=read(root/f'results_{mode}/runs.csv');assert len(rr)==20
    allrows.extend(rr)
fields=['loss_pct','maxLossRun','onTime_pct','handovers','undiscountedReward'];summary=[];paired=[];changes=[]
for mode in ['control','low_lr','large_buffer','soft_target']:
    for ep in [100,200]:
        rr=[r for r in allrows if r['mode']==mode and int(r['episode'])==ep];assert len(rr)==10
        base=[r for r in allrows if r['mode']=='control' and int(r['episode'])==ep]
        assert [r['seed'] for r in rr]==[r['seed'] for r in base]
        for field in fields:
            v=[float(r[field]) for r in rr];d=[float(a[field])-float(b[field]) for a,b in zip(rr,base)]
            half=2.26215716274099*st.stdev(d)/math.sqrt(10)
            summary.append(dict(mode=mode,episode=ep,metric=field,mean=st.mean(v),sampleSD=st.stdev(v),minimum=min(v),maximum=max(v)))
            paired.append(dict(mode=mode,episode=ep,metric=field,differenceVsControl=st.mean(d),pairedCI95_lower=st.mean(d)-half,pairedCI95_upper=st.mean(d)+half))
    a=[r for r in allrows if r['mode']==mode and int(r['episode'])==100];b=[r for r in allrows if r['mode']==mode and int(r['episode'])==200]
    for field in fields:
        d=[float(y[field])-float(x[field]) for x,y in zip(a,b)]
        changes.append(dict(mode=mode,metric=field,meanChange100to200=st.mean(d),sampleSD=st.stdev(d)))
write('summary.csv',summary);write('paired_differences.csv',paired);write('change_100_to_200.csv',changes)
diagnostics=[]
for mode in ['low_lr','large_buffer','soft_target']:
    rr=read(root/f'results_{mode}/learning_diagnostics.csv')
    for ep in [100,200]:
        rows=[r for r in rr if (float(r['episode'])<=100 if ep==100 else float(r['episode'])>100)]
        for metric in ['gradientNorm','clipScale','onlineTargetGap','meanReplayAge_steps','sampleBestSuccessUnder20pct','bufferBestSuccessUnder20pct','probeQbadMinusStay']:
            v=[float(r[metric]) for r in rows if math.isfinite(float(r[metric]))]
            diagnostics.append(dict(mode=mode,phaseEndingEpisode=ep,metric=metric,mean=st.mean(v),minimum=min(v),maximum=max(v),samples=len(v)))
write('diagnostics_summary.csv',diagnostics)
(root/'analysis.json').write_text(json.dumps({'summary':summary,'pairedDifferences':paired,'changes':changes,'controlSource':str(source)},indent=2),encoding='utf8')
for mode in ['control','low_lr','large_buffer','soft_target']:
    for ep in [100,200]:
        d={r['metric']:r['mean'] for r in summary if r['mode']==mode and r['episode']==ep}
        print(json.dumps(dict(mode=mode,episode=ep,**d)))
