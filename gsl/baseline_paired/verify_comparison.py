import csv,json,math,sys
from pathlib import Path
out=Path(sys.argv[1]);ddqn=Path(sys.argv[2])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(r,k):return float(r[k])
baseline=read(out/'baseline_runs.csv');learned=read(ddqn/'runs.csv');checks=read(out/'pairing_checks.csv')
assert len(baseline)==len(learned)==len(checks)==10
records=0
for a,b in zip(baseline,learned):
    assert a['seed']==b['seed'] and a['repeat']==b['repeat']
    folder=f'repeat_{int(a["repeat"]):02}'
    pairs=[read(out/folder/'packets.csv'),read(ddqn/folder/'packets.csv')]
    for p,q in zip(*pairs):
        assert p['packetID']==q['packetID'] and p['time_s']==q['time_s'] and p['phyRandomDraw']==q['phyRandomDraw']
        if p['servingSatID']==q['servingSatID']:
            assert p['snr_dB']==q['snr_dB']
            if float(p['attempted']) and float(q['attempted']):assert p['phyPER']==q['phyPER']
    for run,packets,root in zip((a,b),pairs,(out,ddqn)):
        assert len(packets)==36000
        lost=phy=ho=outage=ontime=received=late=0;start=None;streaks=[]
        for n,p in enumerate(packets,1):
            val=lambda key:float(p[key])
            assert int(p['packetID'])==n and val('outcome_pending')==0
            assert val('lost')+val('received')==1 and val('onTime')+val('late')==val('received')
            assert val('lost')==val('phy_loss')+val('handover_loss')+val('outage_loss')
            assert math.isclose(val('time_s'),(n-1)/60,abs_tol=1e-10)
            lost+=int(val('lost'));phy+=int(val('phy_loss'));ho+=int(val('handover_loss'));outage+=int(val('outage_loss'))
            ontime+=int(val('onTime'));received+=int(val('received'));late+=int(val('late'))
            if val('lost'):
                if start is None:start=n
            elif start is not None:streaks.append((start,n-1,n-start));start=None
        if start is not None:streaks.append((start,n,n-start+1))
        assert lost==int(run['lost'])==phy+ho+outage and received==int(run['received'])
        assert phy==int(run['phyLoss']) and ho==int(run['handoverLoss']) and outage==int(run['outageLoss'])
        assert late==int(run['late'])
        assert math.isclose(lost/360,num(run,'loss_pct'),abs_tol=1e-9)
        assert math.isclose(ontime/360,num(run,'onTime_pct'),abs_tol=1e-9)
        assert max((s[2] for s in streaks),default=0)==int(run['maxLossRun'])
        runs=read(root/folder/'loss_runs.csv')
        assert [(int(r['firstPacketID']),int(r['lastPacketID']),int(r['length_packets'])) for r in runs]==streaks
        decisions=read(root/folder/'decisions.csv')
        count=sum(int(float(r['handoverEvent'])) for r in decisions)
        assert count==int(run['handovers']) and ho==count*6
        records+=len(packets)
    print(f'PAIR PASS {a["repeat"]}: same seed / packet draws, both policies accounting and bursts',flush=True)
report={'status':'PASS','baselineTrainingEpisodes':0,'pairedEvaluationRuns':10,'totalVerifiedPacketRecords':records,'sameChannelAndGeometry':True,'samePacketDraws':True,'ddqnRetrained':False}
(out/'full_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
