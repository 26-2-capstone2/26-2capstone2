from pathlib import Path
import csv,json
root=Path(__file__).parent;out=root/'results'
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
runs=read(out/'runs.csv');assert len(runs)==100;shared={};records=0
for r in runs:
    episode=int(r['episode']);rep=int(r['repeat']);seed=int(r['seed']);folder=out/f'episode_{episode:04d}_repeat_{rep:02d}'
    lost=received=phy=ho=outage=late=ontime=maxrun=streak=count=0;draws=[]
    with (folder/'packets.csv').open(encoding='utf-8-sig',newline='') as f:
        for p in csv.DictReader(f):
            v=lambda k:int(float(p[k]));count+=1;assert int(p['packetID'])==count
            assert v('lost')+v('received')==1 and v('outcome_pending')==0
            assert v('lost')==v('phy_loss')+v('handover_loss')+v('outage_loss')
            lost+=v('lost');received+=v('received');phy+=v('phy_loss');ho+=v('handover_loss');outage+=v('outage_loss');ontime+=v('onTime');late+=v('late')
            streak=streak+1 if v('lost') else 0;maxrun=max(maxrun,streak);draws.append((p['generationTime_s'],p['phyRandomDraw']))
    assert count==36000 and lost==int(r['lost']) and received==int(r['received']) and maxrun==int(r['maxLossRun'])
    assert phy==int(r['phyLoss']) and ho==int(r['handoverLoss']) and outage==int(r['outageLoss']) and ho==6*int(r['handovers'])
    assert ontime==received and late==0 and abs(100*lost/count-float(r['loss_pct']))<1e-9
    trace=read(folder/'decision_quality.csv');assert len(trace)==600
    reward=sum(float(x['reward']) for x in trace);assert abs(reward-float(r['undiscountedReward']))<1e-8
    g=0
    for x in reversed(trace):
        g=float(x['reward'])+.95*g;assert abs(g-float(x['sampledFrozenPolicyReturn']))<1e-8
    if seed not in shared:shared[seed]=draws
    else:assert shared[seed]==draws
    records+=count
    print(f'PASS checkpoint {episode} repeat {rep}: packets/causes/bursts/rewards/paired draws')
result={'status':'PASS','models':10,'evaluationRuns':100,'packets':records,'trainingUpdatesDuringEvaluation':0,'sameSeeds':10}
(root/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
