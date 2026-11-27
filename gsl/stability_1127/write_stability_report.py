from pathlib import Path
import csv,json,hashlib
root=Path(__file__).parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
s=read(root/'summary.csv');probe=read(root/'fixed_probe_summary.csv')
modes=['control','low_lr','large_buffer','soft_target']
labels={'control':'기본 설정','low_lr':'학습률 1e-4','large_buffer':'버퍼 60,000','soft_target':'타깃 1% 반영'}
def metrics(mode,e):return {r['metric']:float(r['mean']) for r in s if r['mode']==mode and int(r['episode'])==e}
lines=['학습 안정성 단일 요인 비교 (2026-11-27)','',
'6×11 / 환경 감쇠 6 dB / Toolbox PHY / GS→첫 위성 / 기존 11개 입력·보상·γ=0.95·Q마진 0.02 유지.',
'각 새 조건 200회 학습. 100회 평가 후 학습을 그대로 이어가며 Adam·버퍼를 초기화하지 않음.',
'평가는 탐험·학습 없이 수행하며 에이전트의 학습 난수를 소비하지 않음.',
'기본 설정은 같은 학습 시드·초기값의 기존 저장 100/200회 모델 평가를 재사용. 계측 클래스 기본 설정과 원본의 행동·손실·가중치 일치 및 타깃 반영 수식을 사전 검증.',
'모든 조건을 동일한 검증 시드 20279301~20279310에서 비교. 신규 60회 + 재사용 20회 평가.','',
'조건 | 학습 횟수 | 손실률(%) | 최대 연속 손실 평균(개) | 기한 내 도착률(%) | 핸드오버(회)']
for mode in modes:
    for e in [100,200]:
        d=metrics(mode,e);lines.append(f"{labels[mode]} | {e} | {d['loss_pct']:.4f} | {d['maxLossRun']:.1f} | {d['onTime_pct']:.4f} | {d['handovers']:.1f}")
lines += ['','100→200회 최대 연속 손실 평균 변화']
for mode in modes:
    a=metrics(mode,100)['maxLossRun'];b=metrics(mode,200)['maxLossRun'];lines.append(f'{labels[mode]}: {a:.1f}→{b:.1f}개 (변화 {b-a:+.1f}개)')
base=metrics('control',200);base100=metrics('control',100)
better=[labels[m] for m in modes[1:] if metrics(m,200)['loss_pct']<base['loss_pct'] and metrics(m,200)['maxLossRun']<base['maxLossRun']]
better100=[labels[m] for m in modes[1:] if metrics(m,200)['loss_pct']<base100['loss_pct'] and metrics(m,200)['maxLossRun']<base100['maxLossRun']]
lines += ['', '관찰된 비교',
'200회 기본 설정 대비 손실률과 최대 연속 손실 평균이 모두 낮은 조건: '+(', '.join(better) if better else '없음'),
'기존 100회 모델 대비 두 지표가 모두 낮은 200회 조건: '+(', '.join(better100) if better100 else '없음'),
'이는 한 초기값·검증 시드 10개의 관찰 결과이며 학습 초기값 반복으로 확정한 결론은 아님.','',
'문제가 됐던 동일 상태(시드 20279302, 1초 시점)에서 각 모델의 선택']
for r in probe:
    lines.append(f"{labels[r['mode']]} {r['episode']}회: 위성 {r['selectedSatID']}, PER {float(r['selectedPER']):.4f}, 최고 Q와 현재 44번 Q의 차이 {float(r['bestQMinusStay44']):.4f}")
lines += ['', '해석 범위와 주의',
'학습률을 시작부터 낮춘 조건은 학습 속도도 다르므로 100/200회만으로 장기 최적 성능을 판정하지 않음.',
'버퍼 20,000은 약 33회, 60,000은 약 100회분 경험을 보관. 버퍼 확대는 희귀 상태의 샘플링 비율을 보장하지 않음.',
'버퍼가 커지면 무작위 표본과 공유 action/replay 난수 경로가 달라질 수 있음. 채널·패킷 난수는 동일하지만 개별 탐험 행동까지 모두 고정한 실험은 아님.',
'부드러운 타깃 반영은 갱신 방식과 평균 타깃 나이를 함께 바꾼 실험임. 타깃의 지연만 단독으로 조절한 것은 아님.',
'진단 기록은 100번 업데이트마다 추출한 표본이며 모든 기울기·리플레이 미니배치를 저장한 것은 아님.',
'대조군보다 나아져도 기존 100회 모델보다 좋은지 구분해야 함. 최종 모델로 자동 교체하지 않음.',
'다른 학습 초기값 반복과 새 최종 평가 시드가 필요하며, 이 결과만으로 원래 1,000회 실험 퇴보의 유일한 원인을 확정하지 않음.',
'checkpoint에는 평가용 네트워크와 설정이 저장됨. 향후 정확한 이어학습에는 버퍼·Adam·난수 상태까지 별도로 보존해야 함.','',
'결과 열기: 상위 gsl의 main_gsl_stability_comparison. 재학습하지 않고 저장된 그림만 엶.']
terminal=read(root/'terminal_sample_summary.csv')
lines += ['', '추가 단서: 600초 종료 경험과 TD 학습 오차',
'에이전트와 같은 RandStream·rand/randi/randperm 호출을 재구성하고, 기록된 표본 경험의 평균 나이가 재구성과 일치하는지 검증함.',
'100회 이후에 100번 업데이트마다 기록한 표본 배치에 대해 다음을 관찰함.']
for r in terminal:
    lines.append(f"{labels[r['mode']]} / 종료 경험 포함={r['containsTerminal']}: 배치 {r['sampledBatches']}개, 평균 Huber loss {float(r['meanHuberLoss']):.5f}, loss>0.1 배치 {r['lossAbovePoint1']}개")
lines += [
'이번 표본에서 loss>0.1은 종료 경험이 포함된 배치에서만 발생했음. 이 상관관계만으로 정책 퇴보의 인과 원인을 확정하지는 않음.',
'현재 11개 입력에는 남은 시간이 직접 포함되지 않지만, 종료 step에서는 bootstrap을 0으로 둠. 마지막 상태의 Q 목표와 비슷한 비종료 상태의 목표가 크게 달라질 수 있는 설계상 위험이 있음.',
'600초가 실제 유한 작업의 끝이라면 남은 시간을 상태에 넣는 방법을, 단순 관측 창이라면 time-limit truncation과 진짜 종료를 구분하는 방법을 검토해야 함.',
'미래 가치 0 처리가 무조건 버그라는 뜻은 아님. 작업의 의미를 고정하고 단일 요인으로 검증해야 함.',
'이번에는 종료 처리·입력 변경을 적용하지 않았고 기존 모델을 보존했음.']
(root/'점검결과.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
print('STABILITY REPORT SAVED')
