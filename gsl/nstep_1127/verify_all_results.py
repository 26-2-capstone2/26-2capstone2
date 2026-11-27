from pathlib import Path
import csv,json
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
jobs=[]
for r in read(root/'results_hysteresis/runs.csv'):
    p=root/'results_hysteresis'/f"h{round(float(r['hysteresis_dB'])*100):03}_repeat_{int(r['repeat']):02}"
    jobs.append((f"H{r['hysteresis_dB']}",r,p))
for n in [1,3,5]:
    b=root/f'results_n{n}';p=b/(b/'latest_result.txt').read_text().strip();t=read(p/'training.csv')
    assert len(t)==100 and [int(r['seed']) for r in t]==list(range(20269101,20269201))
    for r in read(p/'runs.csv'):jobs.append((f'n{n}',r,p/f"repeat_{int(r['repeat']):02}"))
assert len(jobs)==70
reference={};records=0;originalActions={};agreement=[]
for policy,r,p in jobs:
    lost=received=phy=ho=outage=late=ontime=streak=maxrun=count=0;draws=[]
    with (p/'packets.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            count+=1;assert int(row['packetID'])==count and float(row['outcome_pending'])==0
            v=lambda k:int(float(row[k]))
            # The exclusive cause fields are the same as the source packet verifier.
            a=v('lost');b=v('received');assert a+b==1
            lost+=a;received+=b;streak=streak+1 if a else 0;maxrun=max(maxrun,streak)
            phy+=v('phy_loss');ho+=v('handover_loss');outage+=v('outage_loss')
            ontime+=v('onTime');late+=v('late');assert v('phy_loss')+v('handover_loss')+v('outage_loss')==a
            draws.append((row['generationTime_s'],row['phyRandomDraw']))
    assert count==36000 and lost==int(r['lost']) and received==int(r['received']) and maxrun==int(r['maxLossRun'])
    assert phy==int(r['phyLoss']) and ho==int(r['handoverLoss']) and outage==int(r['outageLoss']) and lost==phy+ho+outage
    assert ho==6*int(r['handovers']) and late==0 and ontime==received
    assert abs(100*lost/count-float(r['loss_pct']))<1e-9
    seed=r['seed']
    if seed not in reference:reference[seed]=draws
    else:assert draws==reference[seed]
    if policy.startswith('n'):
        decisions=read(p/'decisions.csv');ids=[int(x['servingSatID']) for x in decisions[:600]]
        if policy=='n1':originalActions[seed]=ids
        else:
            different=sum(a!=b for a,b in zip(ids,originalActions[seed],strict=True))
            agreement.append({'policy':policy,'seed':seed,'differentSelectionsVsN1':different,'totalDecisions':600,'differentSelection_pct':100*different/600})
    records+=count
    print(f'PASS {policy} repeat {r["repeat"]}: {count} packets, paired draws, exclusive causes, max burst')
result={'status':'PASS','evaluationRuns':len(jobs),'packetRecords':records,'pairedSeeds':len(reference),'fullRepeatLogs':True}
(root/'full_verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
with (root/'policy_agreement.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=agreement[0]);w.writeheader();w.writerows(agreement)
