from pathlib import Path
import csv,json,math
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
source=root.parent/'gsl-checkpoint-audit-1127/results'
if not source.exists():source=root.parent/'checkpoint_audit_1127/results'
if not source.exists():source=Path('C:/Users/succe/Desktop/codex/1125/GSL_research_1126/gsl/checkpoint_audit_1127/results')
jobs=[]
for r in read(source/'runs.csv'):
    if int(r['episode']) in [100,200]:jobs.append(('control',r,source/f"episode_{int(r['episode']):04}_repeat_{int(r['repeat']):02}"))
for mode in ['low_lr','large_buffer','soft_target']:
    base=root/f'results_{mode}';t=read(base/'training.csv');assert len(t)==200 and [int(r['seed']) for r in t]==list(range(20269101,20269301))
    for r in read(base/'runs.csv'):jobs.append((mode,r,base/f"episode_{int(r['episode']):04}_repeat_{int(r['repeat']):02}"))
assert len(jobs)==80;reference={};records=0
originalTraining=read(source/'original_training.csv')
bufferTraining=read(root/'results_large_buffer/training.csv')
for a,b in zip(originalTraining[:33],bufferTraining[:33],strict=True):
    for field in ['episode','seed','loss_pct','maxLossRun','handovers','reward','trainingLoss','updates']:
        assert math.isclose(float(a[field]),float(b[field]),rel_tol=0,abs_tol=1e-12),field
for mode,r,folder in jobs:
    seed=r['seed'];lost=received=phy=ho=outage=streak=maxrun=count=0;draws=[]
    with (folder/'packets.csv').open(encoding='utf-8-sig',newline='') as f:
        for p in csv.DictReader(f):
            v=lambda k:int(float(p[k]));count+=1;assert int(p['packetID'])==count and v('outcome_pending')==0
            assert v('received')+v('lost')==1 and v('lost')==v('phy_loss')+v('handover_loss')+v('outage_loss')
            lost+=v('lost');received+=v('received');phy+=v('phy_loss');ho+=v('handover_loss');outage+=v('outage_loss')
            streak=streak+1 if v('lost') else 0;maxrun=max(maxrun,streak);assert v('late')==0 and v('onTime')==v('received')
            draws.append((p['generationTime_s'],p['phyRandomDraw']))
    assert count==36000 and lost==int(r['lost']) and received==int(r['received']) and maxrun==int(r['maxLossRun'])
    assert phy==int(r['phyLoss']) and ho==int(r['handoverLoss']) and outage==int(r['outageLoss']) and ho==6*int(r['handovers'])
    assert abs(100*lost/count-float(r['loss_pct']))<1e-9
    if seed not in reference:reference[seed]=draws
    else:assert reference[seed]==draws
    records+=count
    print(f"PASS {mode} {r['episode']} repeat {r['repeat']}")
result={'status':'PASS','runs':80,'packetRecords':records,'newRuns':60,'reusedControlRuns':20,'pairedEvaluationSeeds':10,'largeBufferFirst33EpisodesReproduceControl':True}
(root/'full_verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
