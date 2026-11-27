from pathlib import Path
import csv,json,statistics as st,math
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
allrows=[]
for r in read(root/'results_hysteresis/runs.csv'):
    r['policy']=f"MaxSNR H={float(r['hysteresis_dB']):g}dB";allrows.append(r)
for n in [1,3,5]:
    base=root/f'results_n{n}';out=base/(base/'latest_result.txt').read_text().strip()
    for r in read(out/'runs.csv'):r['policy']=f'DDQN n={n}';allrows.append(r)
fields=['loss_pct','onTime_pct','maxLossRun','handovers'];policies=list(dict.fromkeys(r['policy'] for r in allrows))
summary=[]
for policy in policies:
    rows=[r for r in allrows if r['policy']==policy];assert len(rows)==10
    for field in fields:
        v=[float(r[field]) for r in rows]
        summary.append({'policy':policy,'metric':field,'mean':st.mean(v),'sampleSD':st.stdev(v),'minimum':min(v),'maximum':max(v)})
paired=[];reference=[r for r in allrows if r['policy']=='DDQN n=1']
for policy in policies:
    if policy=='DDQN n=1':continue
    rows=[r for r in allrows if r['policy']==policy];assert [r['seed'] for r in rows]==[r['seed'] for r in reference]
    for field in fields:
        d=[float(a[field])-float(b[field]) for a,b in zip(rows,reference)]
        half=2.26215716274099*st.stdev(d)/math.sqrt(10)
        paired.append({'policy':policy,'reference':'DDQN n=1','metric':field,'meanDifference':st.mean(d),'pairedCI95_lower':st.mean(d)-half,'pairedCI95_upper':st.mean(d)+half})
for name,rows in [('summary.csv',summary),('paired_differences.csv',paired)]:
    with (root/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
(root/'comparison_report.json').write_text(json.dumps({'summary':summary,'pairedDifferences':paired},indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
