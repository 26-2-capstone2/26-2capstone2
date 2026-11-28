from pathlib import Path
import csv,json,statistics as st
root=Path(__file__).parent
with (root/'summary.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
policies=list(dict.fromkeys(r['policy'] for r in rows))
lines=['GSL 최대 SNR 히스테리시스 및 n-step DDQN 실험','2026-11-27','',
'6×11 / 환경 감쇠 6 dB / Toolbox PHY / GS→첫 위성 / 600초·36,000개 패킷',
'같은 새로운 평가 시드 10개(20279301~20279310). 이전 10회 평가 수치와 섞지 않음.','',
'정책 | 손실률(%) | 최대 연속 손실 평균(개) | 기한 내 도착률(%) | 핸드오버(회)']
for policy in policies:
    d={r['metric']:float(r['mean']) for r in rows if r['policy']==policy}
    lines.append(f"{policy} | {d['loss_pct']:.4f} | {d['maxLossRun']:.1f} | {d['onTime_pct']:.4f} | {d['handovers']:.1f}")
lines += ['', '학습 조건',
'1/3/5-step 모두 100회, 같은 초기 가중치·학습 시드·11개 입력·64-64 구조·γ=0.95·보상 1/0.3/0.1·Q마진 0.02.',
'기존 보상: 기한 내 수신 비율 - 0.3×평균 min(streak/60,10) - 0.1×핸드오버.',
'실제 전환 중단 100 ms는 동일. PHY나 송수신 조건을 조절하지 않음.',
'n-step은 최대 경험 길이이며, 중간에 온라인 Q의 최대 행동과 다른 행동(탐험·Q마진 유지 포함)이 나오면 그 행동 직전에서 묶음을 끊음.',
'종료 시 남은 경험도 처리. 종료 이후 보상은 붙이지 않음. bootstrap 할인은 실제 묶인 길이 h에 맞춰 γ^h.',
'저장 당시의 greedy 여부를 사용하는 실용적 보정이며, 함수 근사·오래된 replay에 대한 완전한 비편향성을 주장하지 않음.','',
'실제 사용된 학습 길이']
for n in [1,3,5]:
    base=root/f'results_n{n}';out=base/(base/'latest_result.txt').read_text().strip()
    with (out/'nstep_target_stats.csv').open(encoding='utf-8-sig',newline='') as f:t=list(csv.DictReader(f))
    total=sum(int(r['count']) for r in t);mean=sum(int(r['effectiveHorizon'])*int(r['count']) for r in t)/total
    lines.append(f"n={n}: 경험 {total}개, 평균 길이 {mean:.3f}, 길이별 수 "+str({r['effectiveHorizon']:int(r['count']) for r in t}))
lines += ['', '이번 결과 해석',
'3-step과 5-step은 1-step보다 손실률과 최대 연속 손실 평균을 개선하지 못했다. 기존 1-step 모델을 교체하지 않는다.',
'최대 SNR 0.3 dB 대비 1-step은 손실률 4.9061%→3.8144%, 최대 연속 손실 44.1→39.7개, 전환 195.2→135.9회로 평균이 낮았다.',
'최대 SNR 0.1 dB의 최대 연속 손실 평균 36.9개는 1-step 39.7개보다 낮았으나, 손실률·전환은 더 높았다. 모든 지표에서 일관되게 우월한 방식이라고 결론 내리지 않는다.',
'3-step과 5-step은 1-step 대비 각각 8.50%, 6.55%의 결정 시점에서 다른 위성을 선택했다. 완전히 같은 정책은 아니지만 대부분의 선택은 비슷했다.',
'실제 평균 학습 길이는 3-step 약 1.991초, 5-step 약 2.613초였다. 중간 비최대 행동에서 경험을 끊은 결과다.',
'라이선스 오류로 시작하지 못한 최초 5-step 배치는 실험 결과에 포함하지 않았다. R2026a 단독 재실행으로 새로 100회를 학습했다.',
'70회 평가·2,520,000개 패킷의 독립 재계산과 같은 후보 SNR·난수 사용 검증 통과. 1-step 최종 네트워크는 기존 100회 모델 가중치와 정확히 일치.',
'', '해석 시 주의',
'이번 실험은 초기값 하나씩 학습한 탐색적 비교. 10개 평가 시드는 학습 초기값 10개와 다름.',
'보상을 고정했으므로, 누적 연속 손실 비용과 최대 연속 손실 평가 지표의 차이 자체는 남아 있음.',
'세 방식의 평가 시드·기하·후보 SNR·패킷 난수는 동일. 평균 및 표준편차와 paired 차이는 CSV에 저장.',
'paired 95% 구간은 평가 시드 변동만 나타내며 여러 비교에 대한 보정이나 학습 초기값 변동을 포함하지 않음.',
'n-step 경험 삽입 지연 때문에 3/5-step은 첫 업데이트가 1-step보다 한 번 늦을 수 있음. 1-step은 원본 재현을 우선함.',
'히스테리시스에 따라 손실률·전환·연속 손실의 상충을 함께 보고, 낮은 손실률 하나만으로 최종 정책을 고르지 않음.','',
'결과 열기',
'상위 gsl 폴더에서 main_gsl_nstep_comparison 실행: 저장된 그래프만 열고 학습하지 않음.',
'개별 DDQN 패킷 보기: addpath nstep_1127; open_saved_gsl_nstep_model(1), (3), (5).',
'재학습은 nstep_1127/train_n1.m, train_n3.m, train_n5.m을 명시적으로 실행할 때만 진행.']
(root/'실험결과.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
print('REPORT SAVED')
