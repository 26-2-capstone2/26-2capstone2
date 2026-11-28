import csv,json,math
from pathlib import Path
root=Path(__file__).parent/'validation_new_seeds'
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
runs=read(root/'runs.csv');assert len(runs)==20
records=0
for r in runs:
    folder=root/f'{r["mode"]}_repeat_{int(r["repeat"]):02}'
    count=lost=received=phy=ho=outage=ontime=late=pending=0
    streak=maxrun=0
    with (folder/'packets.csv').open(encoding='utf-8-sig',newline='') as f:
        for i,p in enumerate(csv.DictReader(f),1):
            num=lambda k:float(p[k])
            assert int(p['packetID'])==i
            assert num('received')+num('lost')+num('outcome_pending')==1
            assert num('lost')==num('phy_loss')+num('handover_loss')+num('outage_loss')
            assert num('onTime')+num('late')==num('received')
            lost+=int(num('lost'));received+=int(num('received'));phy+=int(num('phy_loss'))
            ho+=int(num('handover_loss'));outage+=int(num('outage_loss'))
            ontime+=int(num('onTime'));late+=int(num('late'));pending+=int(num('outcome_pending'))
            streak=streak+1 if num('lost') else 0;maxrun=max(maxrun,streak);count=i
    assert count==int(r['generated'])==36000
    assert lost==int(r['lost']) and received==int(r['received'])
    assert phy==int(r['phyLoss']) and ho==int(r['handoverLoss']) and outage==int(r['outageLoss'])
    assert late==pending==0 and maxrun==int(r['maxLossRun'])
    assert math.isclose(100*lost/count,float(r['loss_pct']),abs_tol=1e-9)
    assert math.isclose(100*ontime/count,float(r['onTime_pct']),abs_tol=1e-9)
    assert ho==6*int(r['handovers'])
    records+=count
for repeat in range(1,11):
    a=root/f'control_repeat_{repeat:02}'/'packets.csv'
    b=root/f'peak_repeat_{repeat:02}'/'packets.csv'
    with a.open(encoding='utf-8-sig',newline='') as fa,b.open(encoding='utf-8-sig',newline='') as fb:
        for pa,pb in zip(csv.DictReader(fa),csv.DictReader(fb),strict=True):
            assert pa['packetID']==pb['packetID']
            assert pa['phyRandomDraw']==pb['phyRandomDraw']
            assert pa['generationTime_s']==pb['generationTime_s']
result={'status':'PASS','runs':20,'packets':records,'pairedDrawsVerified':True,'newSeeds':'20278001:20278010'}
(root/'full_verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
