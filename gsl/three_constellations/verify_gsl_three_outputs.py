import csv, hashlib, json, math, sys
from pathlib import Path
root=Path(sys.argv[1])
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(r,k):return float(r[k])
runs=read(root/'runs.csv');manifest=read(root/'log_manifest.csv')
assert len(runs)==len(manifest)==90
assert len(read(root/'summary.csv'))==9
draw_hash={}; packet_total=0; delivered_total=0
for run in runs:
    a,b=int(run['planes']),int(run['satellitesPerPlane']); repeat=int(run['repeat']);policy=run['policy']
    folder=root/f'grid_{a}x{b}'/policy;stem=f'repeat_{repeat:02}'
    flags={'received':0,'lost':0,'phyLoss':0,'handoverLoss':0,'outageLoss':0,'late':0,'onTime':0}
    fields={'received':'received','lost':'lost','phyLoss':'phy_loss','handoverLoss':'handover_loss','outageLoss':'outage_loss','late':'late','onTime':'onTime'}
    expected=[];start=None;received={};h=hashlib.sha256()
    with (folder/f'{stem}_packets.csv').open(encoding='utf-8-sig',newline='') as f:
        for n,r in enumerate(csv.DictReader(f),1):
            assert int(r['packetID'])==n and num(r,'outcome_pending')==0
            assert num(r,'received')+num(r,'lost')==1
            assert num(r,'lost')==sum(num(r,k) for k in ('phy_loss','handover_loss','outage_loss'))
            assert num(r,'onTime')+num(r,'late')==num(r,'received')
            assert math.isclose(num(r,'time_s'),(n-1)/60,abs_tol=1e-10)
            assert math.isclose(num(r,'transmission_delay_ms'),.04096,abs_tol=1e-12)
            h.update(r['phyRandomDraw'].encode()+b'\n')
            if num(r,'attempted'):
                assert r['phyStatus']=='TOOLBOX_QPSK_AR4JA_AWGN_EMPIRICAL'
                p=num(r,'phyPER');lo=num(r,'phyPER_lower95');hi=num(r,'phyPER_upper95')
                assert 0<=p<=1 and lo<=p+1e-10 and hi>=p-1e-10
            for key,col in fields.items():flags[key]+=int(num(r,col))
            if num(r,'lost'):
                if start is None:start=n
            elif start is not None:expected.append((start,n-1,n-start));start=None
            if num(r,'received'):
                assert num(r,'arrivalTime_s')>=num(r,'generationTime_s')
                assert num(r,'onTime')==(num(r,'arrivalTime_s')<=num(r,'deadlineTime_s'))
                received[n]=[num(r,k) for k in ('generationTime_s','arrivalTime_s','destinationSatelliteID','destinationPlaneIndex','destinationSatelliteInPlane','onTime')]
    if start is not None:expected.append((start,n,n-start+1))
    assert n==int(run['generated'])==36000
    for key in ('received','lost','phyLoss','handoverLoss','outageLoss','late'):assert flags[key]==int(run[key])
    assert math.isclose(100*flags['lost']/n,num(run,'loss_pct'),abs_tol=1e-9)
    assert math.isclose(100*flags['onTime']/n,num(run,'onTime_pct'),abs_tol=1e-9)
    assert math.isclose(num(run,'loss_pct'),num(run,'verifiedLoss_pct'),abs_tol=1e-9)
    assert flags['handoverLoss']==int(run['handovers'])*6
    lossruns=read(folder/f'{stem}_loss_runs.csv')
    assert [(int(x['firstPacketID']),int(x['lastPacketID']),int(x['length_packets'])) for x in lossruns]==expected
    assert max((x[2] for x in expected),default=0)==int(run['maxLossRun'])
    decisions=read(folder/f'{stem}_decisions.csv');assert len(decisions)==601
    assert sum(int(float(x['handoverEvent'])) for x in decisions)==int(run['handovers'])
    incoming=read(folder/f'{stem}_isl_input.csv');assert len(incoming)==flags['received']
    assert {int(x['packet_id']) for x in incoming}==set(received)
    for x in incoming:
        actual=[num(x,k) for k in ('generation_time_s','isl_entry_time_s','satellite_id','p_zero_based','s_zero_based','gsl_on_time')]
        assert all(math.isclose(u,v,abs_tol=1e-10) for u,v in zip(actual,received[int(x['packet_id'])]))
        assert int(x['p'])==int(x['p_zero_based'])+1 and int(x['s'])==int(x['s_zero_based'])+1
        assert int(x['satellite_id'])==(int(x['p'])-1)*b+int(x['s'])
        assert int(x['packet_size_bytes'])==160
        assert int(x['flow_id'])==0
    key=(a,b,int(run['seed']));digest=h.hexdigest()
    if key in draw_hash:assert draw_hash[key]==digest
    draw_hash[key]=digest
    packet_total+=n;delivered_total+=len(incoming)
    print(f'PASS {a}x{b} {policy} repeat {repeat:02}: 36,000 packet records and {len(incoming):,} ISL arrivals',flush=True)
for a,b in ((6,11),(20,20),(36,36)):
    for repeat in range(1,11):
        with (root/f'grid_{a}x{b}'/f'repeat_{repeat:02}_candidates.csv').open(encoding='utf-8-sig',newline='') as f:
            times=set()
            for x in csv.DictReader(f):
                assert num(x,'elevation_deg')>=25 and 1<=int(x['satellite_id'])<=a*b
                assert int(x['satellite_id'])==(int(x['p'])-1)*b+int(x['s'])
                times.add(int(num(x,'time_s')))
            assert times==set(range(600))
report={'status':'PASS','scope':'GS to first satellite only','runs':90,'packet_records':packet_total,'isl_arrival_records':delivered_total,'paired_channel_and_packet_seeds':30,'candidate_tables':30,'all_repeats_saved':True}
(root/'full_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
