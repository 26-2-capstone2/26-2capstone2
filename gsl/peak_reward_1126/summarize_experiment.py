import csv,json,math,statistics as st
from pathlib import Path

root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def result(mode):
    base=root/f'results_{mode}'
    return base/(base/'latest_result.txt').read_text().strip()
fields=['loss_pct','maxLossRun','onTime_pct','handovers']
cohorts={'original':{m:read(result(m)/'runs.csv') for m in ('control','peak')}}
fresh=read(root/'validation_new_seeds/runs.csv')
cohorts['fresh']={m:[r for r in fresh if r['mode']==m] for m in ('control','peak')}
summary=[];diffs=[]
for cohort,arms in cohorts.items():
    assert len(arms['control'])==len(arms['peak'])==10
    assert [r['seed'] for r in arms['control']]==[r['seed'] for r in arms['peak']]
    for mode,rows in arms.items():
        for field in fields:
            vals=[float(r[field]) for r in rows]
            summary.append(dict(cohort=cohort,mode=mode,metric=field,mean=st.mean(vals),sampleSD=st.stdev(vals),minimum=min(vals),maximum=max(vals)))
    for field in fields:
        d=[float(b[field])-float(a[field]) for a,b in zip(arms['control'],arms['peak'])]
        half=2.262157*st.stdev(d)/math.sqrt(10)
        diffs.append(dict(cohort=cohort,metric=field,peakMinusControl=st.mean(d),pairedCI95Lower=st.mean(d)-half,pairedCI95Upper=st.mean(d)+half))

checks=0
for cohort,arms in cohorts.items():
    for mode,rows in arms.items():
        for r in rows:
            folder=(result(mode)/f'repeat_{int(r["repeat"]):02d}' if cohort=='original' else root/'validation_new_seeds'/f'{mode}_repeat_{int(r["repeat"]):02d}')
            trace=read(folder/('objective_trace.csv' if cohort=='original' else 'Q_return_trace.csv'))
            if mode=='peak':
                expected=-(float(r['lost'])+.3*float(r['maxLossRun']))/60
                assert abs(sum(float(t['reward']) for t in trace)-expected)<1e-8
                checks+=1
manifest=json.loads((root/'experiment_manifest.json').read_text())
import hashlib
for name,digest in manifest['preservedSHA256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest().lower()==digest.lower(),name
for name,rows in [('comparison_summary.csv',summary),('paired_differences.csv',diffs)]:
    with (root/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
report={'summary':summary,'pairedDifferences':diffs,'peakObjectiveIdentitiesVerified':checks,'preservedOriginalHashes':'PASS',
        'limitations':['one training initialization per arm','original seed cohort previously used; fresh cohort is additional held-out evaluation','both arms use new common protocol; not an isolated comparison to historical 12-input model','CI describes evaluation-seed variation, not training-seed variation']}
(root/'comparison_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
lines=['보상식 개선 실험 결과 (2026-11-26)','',
       '6×11 / 환경 감쇠 6 dB / GS → 첫 위성 / 600초·36,000패킷',
       '두 방식 각각 100회 학습, 기존 평가 조건 10개 + 새로운 평가 조건 10개.',
       '학습에 쓰지 않은 동일 조건끼리 비교. PHY와 실제 핸드오버 중단 시간은 유지.', '',
       '비교 방식',
       '누적 벌점: 매 패킷의 현재 연속 손실 길이에 비례한 비용을 계속 더함.',
       '최대 길이 벌점: 이번 실행에서 최대 연속 손실 기록이 늘어날 때만 그 증가량만큼 벌점.',
       '새 보상 총합 = -(전체 손실 패킷 수 + 0.3 × 최대 연속 손실 길이) / 60.',
       '두 방식 모두 14개 입력, 할인율 1, 별도 핸드오버 벌점 없음. 실제 전환 손실은 그대로 포함.',
       '따라서 과거 12개 입력·할인율 0.95 모델과의 차이를 보상식 하나의 효과로 해석하면 안 됨.','']
for cohort,label in [('original','기존 평가 조건 10개 평균'),('fresh','새 평가 조건 10개 평균')]:
    lines.append(label)
    for mode,korean in [('control','누적 벌점'),('peak','최대 길이 벌점')]:
        s={x['metric']:x['mean'] for x in summary if x['cohort']==cohort and x['mode']==mode}
        worst=max(float(r['maxLossRun']) for r in cohorts[cohort][mode])
        lines.append(f"{korean}: 손실률 {s['loss_pct']:.4f}%, 최대 연속 손실 평균 {s['maxLossRun']:.1f}개 (가장 긴 기록 {worst:.0f}개), 기한 내 도착률 {s['onTime_pct']:.4f}%, 핸드오버 {s['handovers']:.1f}회")
    lines.append('')
lines += ['해석 및 한계',
          '이번 실험에서는 손실률과 핸드오버는 감소했지만 최대 연속 손실은 두 평가 묶음 모두 평균이 증가했음. 연속 손실 개선 성공으로 볼 수 없으며 기존 최종 모델을 교체하지 않음.',
          '새 조건에서는 최대 연속 손실 평균이 36.8개에서 46.6개, 최악 기록이 70개에서 129개로 증가했음.',
          '계수 0.3은 연속 손실 10개 증가를 전체 손실 3개 증가와 같은 비용으로 취급함. 전체 손실 감소를 위해 최대 연속 손실 증가를 허용할 수 있는 목표임.',
          '보상식과 목표 지표가 수학적으로 일치하는 것은 확인했지만, 그 자체가 학습 성능 개선을 보장하지는 않음.',
          '기존 조건과 새로운 조건에서 최대 연속 손실이 모두 줄어드는지 확인해 채택 여부를 판단해야 함.',
          '손실률과 최대 연속 손실을 함께 고려하는 가중합이며, 연속 손실만 무조건 최소화하는 목표는 아님.',
          '각 방식의 학습은 한 번씩만 수행했으므로 여러 학습 초기값에 대한 안정성은 아직 검증하지 않음.',
          'paired_differences.csv의 95% 구간은 같은 평가 조건의 차이에 대한 구간이며 학습 초기값의 불확실성은 포함하지 않음.',
          '검증: 전체 패킷 기록 별도 재계산, 보상 총합 등식 20회 확인, 기존 모델·물리 계산 파일 원본 해시 유지.', '',
          '실행: 상위 gsl 폴더에서 main_gsl_peak_reward 실행. 저장된 비교 그림과 패킷 뷰어만 열며 재학습하지 않음.',
          '새 학습은 start_control.m / start_peak.m을 명시적으로 실행할 때만 진행.']
(root/'실험결과.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
print(json.dumps({'summary':summary,'pairedDifferences':diffs,'objectiveChecks':checks},indent=2))
