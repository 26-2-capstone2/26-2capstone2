import csv,json,math,sys
from pathlib import Path
root=Path(sys.argv[1])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(r,k):return float(r[k])
train=read(root/'training.csv');runs=read(root/'runs.csv')
assert len(train)==100 and len(runs)==10
assert set(x['seed'] for x in train).isdisjoint(x['seed'] for x in runs)
records=0
for run in runs:
    folder=root/f'repeat_{int(run["repeat"]):02}'
    received={};lost=phy=ho=outage=late=ontime=0;start=None;streaks=[]
    for n,p in enumerate(read(folder/'packets.csv'),1):
        assert int(p['packetID'])==n and num(p,'outcome_pending')==0
        assert num(p,'received')+num(p,'lost')==1
        assert num(p,'lost')==sum(num(p,k) for k in ('phy_loss','handover_loss','outage_loss'))
        assert num(p,'onTime')+num(p,'late')==num(p,'received')
        assert math.isclose(num(p,'time_s'),(n-1)/60,abs_tol=1e-10)
        assert math.isclose(num(p,'transmission_delay_ms'),.04096,abs_tol=1e-12)
        lost+=int(num(p,'lost'));phy+=int(num(p,'phy_loss'));ho+=int(num(p,'handover_loss'))
        outage+=int(num(p,'outage_loss'));late+=int(num(p,'late'));ontime+=int(num(p,'onTime'))
        if num(p,'lost'):
            if start is None:start=n
        elif start is not None:streaks.append((start,n-1,n-start));start=None
        if num(p,'received'):
            assert num(p,'arrivalTime_s')>=num(p,'generationTime_s')
            received[n]=[num(p,k) for k in ('generationTime_s','arrivalTime_s','destinationSatelliteID','destinationPlaneIndex','destinationSatelliteInPlane','onTime')]
    if start is not None:streaks.append((start,n,n-start+1))
    assert n==int(run['generated'])==36000
    assert lost==int(run['lost'])==phy+ho+outage
    assert phy==int(run['phyLoss']) and ho==int(run['handoverLoss']) and outage==int(run['outageLoss'])
    assert len(received)==int(run['received']) and late==int(run['late'])
    assert math.isclose(100*lost/n,num(run,'loss_pct'),abs_tol=1e-9)
    assert math.isclose(100*ontime/n,num(run,'onTime_pct'),abs_tol=1e-9)
    assert math.isclose(num(run,'loss_pct'),num(run,'verifiedLoss_pct'),abs_tol=1e-9)
    assert max((s[2] for s in streaks),default=0)==int(run['maxLossRun'])
    actual=read(folder/'loss_runs.csv')
    assert [(int(x['firstPacketID']),int(x['lastPacketID']),int(x['length_packets'])) for x in actual]==streaks
    decisions=read(folder/'decisions.csv');assert len(decisions)==601
    switches=sum(int(num(x,'handoverEvent')) for x in decisions)
    assert switches==int(run['handovers']) and ho==switches*6
    arrivals=read(folder/'isl_input.csv');assert len(arrivals)==len(received)
    assert set(int(x['packet_id']) for x in arrivals)==set(received)
    for x in arrivals:
        values=[num(x,k) for k in ('generation_time_s','isl_entry_time_s','satellite_id','p_zero_based','s_zero_based','gsl_on_time')]
        assert all(math.isclose(a,b,abs_tol=1e-10) for a,b in zip(values,received[int(x['packet_id'])]))
        assert int(x['flow_id'])==0 and int(x['satellite_id'])==(int(x['p'])-1)*11+int(x['s'])
    times=set()
    for x in read(folder/'candidates.csv'):
        assert num(x,'elevation_deg')>=25 and 1<=int(x['satellite_id'])<=66
        times.add(int(num(x,'time_s')))
    assert times==set(range(600))
    records+=n;print(f'PASS repeat {run["repeat"]}: {n} packets, all causes / bursts / arrivals / candidates',flush=True)
result={'status':'PASS','scope':'GS to first satellite only','trainingEpisodes':100,'evaluationRuns':10,'packetRecords':records,'trainTestSeedsDisjoint':True,'allRepeatsSaved':True}
(root/'full_verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result),flush=True)
