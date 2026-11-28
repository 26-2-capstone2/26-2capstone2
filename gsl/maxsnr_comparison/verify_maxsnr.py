import csv,json,math,sys
from pathlib import Path
out=Path(sys.argv[1]);source=Path(sys.argv[2])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
runs=read(out/'maxsnr_runs.csv');assert len(runs)==10
ddqn=read(source/'runs.csv');total=0
for r,d in zip(runs,ddqn):
    assert r['seed']==d['seed'] and r['repeat']==d['repeat']
    folder=f'repeat_{int(r["repeat"]):02}'
    maxima={}
    for c in read(source/folder/'candidates.csv'):
        t=int(float(c['time_s']));value=float(c['snr_dB'])
        maxima[t]=max(maxima.get(t,-math.inf),value)
    L=read(out/folder/'decisions.csv');assert len(L)==601
    changes=0;old=0
    for t,x in enumerate(L[:600]):
        assert math.isclose(float(x['snr_dB']),maxima[t],abs_tol=1e-10)
        id=int(x['servingSatID']);change=int(old>0 and id>0 and old!=id)
        assert change==int(x['handoverEvent']);changes+=change;old=id
    P=read(out/folder/'packets.csv');D=read(source/folder/'packets.csv');assert len(P)==len(D)==36000
    lost=received=phy=ho=outage=onTime=late=0;start=None;bursts=[]
    for n,(p,q) in enumerate(zip(P,D),1):
        v=lambda k:float(p[k])
        assert int(p['packetID'])==n and p['packetID']==q['packetID'] and p['phyRandomDraw']==q['phyRandomDraw']
        assert v('outcome_pending')==0 and v('lost')+v('received')==1
        assert v('lost')==v('phy_loss')+v('handover_loss')+v('outage_loss')
        assert v('onTime')+v('late')==v('received')
        assert math.isclose(v('time_s'),(n-1)/60,abs_tol=1e-10)
        lost+=int(v('lost'));received+=int(v('received'));phy+=int(v('phy_loss'));ho+=int(v('handover_loss'))
        outage+=int(v('outage_loss'));onTime+=int(v('onTime'));late+=int(v('late'))
        if p['servingSatID']==q['servingSatID']:
            assert p['snr_dB']==q['snr_dB']
            if v('attempted') and float(q['attempted']):assert p['phyPER']==q['phyPER']
        if v('lost'):
            if start is None:start=n
        elif start is not None:bursts.append((start,n-1,n-start));start=None
    if start is not None:bursts.append((start,n,n-start+1))
    assert lost==int(r['lost'])==phy+ho+outage and received==int(r['received'])
    assert phy==int(r['phyLoss']) and ho==int(r['handoverLoss']) and outage==int(r['outageLoss'])
    assert late==int(r['late']) and changes==int(r['handovers']) and ho==changes*6
    assert math.isclose(lost/360,float(r['loss_pct']),abs_tol=1e-9)
    assert math.isclose(onTime/360,float(r['onTime_pct']),abs_tol=1e-9)
    assert max((x[2] for x in bursts),default=0)==int(r['maxLossRun'])
    B=read(out/folder/'loss_runs.csv')
    assert [(int(b['firstPacketID']),int(b['lastPacketID']),int(b['length_packets'])) for b in B]==bursts
    total+=len(P);print(f'MAX-SNR PASS {r["repeat"]}: every decision greedy, paired draws, all packets and bursts',flush=True)
report={'status':'PASS','maxSNRTrainingEpisodes':0,'newEvaluationRuns':10,'newVerifiedPacketRecords':total,'greedyChoicesChecked':6000,'samePacketDraws':True,'sameChannelAndPHY':True,'existingResultsReused':True}
(out/'full_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
