from pathlib import Path
import csv,json,math
root=Path(__file__).parent;out=root/'results'
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def maxrun(values):
    s=m=0
    for v in values:s=s+1 if v else 0;m=max(m,s)
    return m
rows=read(out/'cases.csv');assert len(rows)==30;records=0;shared={}
for r in rows:
    n=int(r['nStep']);rep=int(r['repeat']);seed=int(r['seed']);p=out/f'n{n}_repeat_{rep:02d}_packet_comparison.csv'
    old=[];new=[];bound=[];per=[]
    for i,x in enumerate(read(p),1):
        assert int(x['packetID'])==i
        a=int(x['originalLost']);b=int(x['counterfactualLost']);v=int(x['optimisticAllCandidatesFail']);assert v<=a and v<=b
        old.append(a);new.append(b);bound.append(v);per.append(float(x['bestCandidatePER']))
    assert len(old)==36000
    assert maxrun(old)==int(r['originalMaxRun']) and maxrun(new)==int(r['counterfactualGlobalMax'])
    assert maxrun(bound)==int(r['optimisticGlobalMax'])
    assert sum(old)==int(r['originalFullLost']) and sum(new)==int(r['counterfactualFullLost'])
    a=int(r['firstPacketID'])-1;b=int(r['lastPacketID']);assert all(old[a:b]) and b-a==int(r['originalMaxRun'])
    assert sum(bound[a:b])==int(r['allCandidatesFailPacketsInBurst'])
    assert sum(p==1 for p in per[a:b])==int(r['allCandidatesPER1PacketsInBurst'])
    assert int(r['burstPHYLoss'])+int(r['burstHOLoss'])==b-a
    if seed not in shared:shared[seed]=(bound,per)
    else:assert shared[seed]==(bound,per)
    records+=len(old)
result={'status':'PASS','cases':30,'packetComparisons':records,'sharedLowerBoundBySeed':True,'lowerBoundSubsetOfOriginalAndCounterfactual':True}
(root/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
