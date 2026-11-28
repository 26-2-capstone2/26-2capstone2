정적 GSL DDQN 보상 비교 (2026-11-28)

gsl 폴더에서 실행:
R = main_gsl_static_reward_comparison('run');
보상별 100회씩 새로 학습한 뒤, 각 모델을 Q 마진 0 / 0.02로 10회씩 평가한다.
MaxSNR + 0.1dB도 같은 평가 시드 10개로 평가한다.
총 학습 200회, 평가 50회이며, 기존 이동 환경에서 학습한 모델을 사용하지 않는다.
완료 결과 다시 열기: main_gsl_static_reward_comparison
짧은 실행 확인: main_gsl_static_reward_comparison('smoke')
smoke는 각 2회 학습/2개 평가 시드이며 실제 성능 비교 결과가 아니다.

설정 파일: static_reward_1128/configGSLStaticReward.m
환경: 정적 6x11, GS는 첫 열 근처, 회차별 방향/오프셋 무작위,
고도각 25도 이상 모든 위성이 후보. 위치/각도는 600초 고정.
SNR은 1초마다 변화(표준편차 1dB, 상관시간 5초), 환경감쇠 6dB.
기존 Toolbox QPSK+AR4JA AWGN PER 표와 패킷/핸드오버 모델 유지.
ISL 내부 전송은 실행하지 않으며 GS -> 첫 위성까지만 평가한다.

보상 = 기한 내 수신 비율 - burst * mean(min((streak/L0)^power,cap)) - handover * HO
linear: onTime=1, burst=0.3, L0=60, power=1, cap=10, handover=0.1
quadratic: onTime=1, burst=0.15, L0=12, power=2, cap=25, handover=0.03
streak는 각 패킷의 누적 연속 손실 수, 정상 수신 시 0, 초 경계에서도 이어진다.
수정안의 보상 범위는 -3.78~1.00이며, 최대 연속 손실 자체를 직접 최적화하는 것은 아니다.
신경망 11-64-64-1, 할인율 0.95, 학습률 0.0003 등 기존 설정 유지.
훈련은 양쪽 모두 Q 마진 0.02. 평가는 탐색 없이 Q 마진만 0 / 0.02로 변경한다.
Q 마진은 dB가 아니다. 선택은 매 1초마다이며 초 중간 즉시 전환은 하지 않는다.
epsilon은 기존과 같이 80회에 걸쳐 1 -> 0.05로 감소한다.

학습 시드 20281001~20281100, 평가 시드 20282001~20282010은 서로 겹치지 않는다.
양쪽은 동일한 초기 가중치/학습 시드/초기 배치/SNR/패킷 난수로 시작한다.
보상에 따라 정책과 실제 탐색 경로는 달라질 수 있다.
평가는 동일 시드별로 배치/SNR/패킷 난수를 정확히 공유하고 가중치를 갱신하지 않는다.
이번 비교는 보상식 구성 전체의 비교다. 가중치별 개별 효과를 분리한 실험은 아니다.
신경망 초기화 시드는 1개이므로 최종 결론에는 여러 학습 초기화로 재현 검증이 필요하다.
기존 600초 종료 처리 등은 변경하지 않았다.

결과: static_reward_1128/results/<실행시간>/
summary.csv: 정책별 10회 평균/표준편차/최솟값/최댓값
runs.csv: 모든 반복의 손실률/기한 내 도착률/최대 연속 손실/핸드오버
paired_changes.csv: 같은 Q 마진에서 수정안 - 기존안, 같은 시드별 차이
comparison.fig/png: 4개 평가 지표 비교(오차막대는 표준편차)
linear_training.csv, quadratic_training.csv: 회차별 학습 기록
*_initial.mat, *_agent_*.mat: 초기/10회 간격/최종 신경망 저장
체크포인트는 추론용 가중치이며 중단 지점부터 정확한 학습 재개 기능은 제공하지 않는다.
정책별/repeat_01~10/packets.csv, decisions.csv, loss_runs.csv, satellites.csv
environment.mat에는 배치/전체 SNR/PER/공유 패킷 난수를 저장한다.
decisions.csv의 studyReward/onTimeReward/streakCost/handoverCost는 해당 실험 보상이다.
상위 클래스 rewardHistory는 기존 계산용이므로 이 실험의 보상 확인에는 사용하지 않는다.
전체 반복 로그가 저장되며 첫 반복만 저장하는 방식이 아니다.

검증: addpath('static_reward_1128'); verifyStaticReward
기존 보상 재현, 수정 보상 수치/클리핑, 두 보상의 동일 행동 시 동일 물리 결과,
36000개 패킷의 기준 계산과 일치를 확인한다.
