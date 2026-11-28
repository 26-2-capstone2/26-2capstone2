정적 GSL: 최고 SNR / 최고 고도각 / DDQN 비교 (2026-11-28)

실행: main_gsl_static_policy_comparison('run')
완료 결과 열기: main_gsl_static_policy_comparison

6x11 정적 위성 배치, GS 첫 열 근처, 최소 고도각 25도.
회차별 방향/작은 위치 오프셋은 랜덤, 각 회차 600초 동안 좌표/각도 고정.
SNR은 매초 시간상관 랜덤 변동(표준편차 1dB, 상관시간 5초).
감쇠 6dB, Toolbox QPSK+AR4JA AWGN PER 표, 160바이트, 60pps, 36000패킷.
100ms 핸드오버 중단, GS -> 첫 위성만 평가. ISL 내부는 포함하지 않는다.

1. MaxSNR_0dB: 추가 히스테리시스 없이 매초 최고 SNR 후보 선택, 학습 없이 10회 평가.
2. Elevation_4deg: 최고 고도각 선택, 기존 4도 전환 마진 유지, 학습 없이 10회 평가.
   정적 환경에서는 후보별 각도가 고정되므로 최고 고도각 위성을 계속 유지한다.
3. quadratic_Q0.02: 수정 보상식으로 DDQN 100회 새로 학습, 탐색 없이 10회 평가.
   보상 = 기한 내 수신 비율 -0.15*mean(min((streak/12)^2,25))-0.03*HO.
   Q 마진은 0.02이며 dB가 아니다. 신경망 11-64-64-1, 할인율 0.95.

모든 평가: 시드 20282001~20282010, 동일 배치/SNR/PER/패킷 난수.
학습: 시드 20281001~20281100, 평가 시드와 분리.
신경망 초기화 시드는 1개. 평가 10회는 재학습 10번을 뜻하지 않는다.
기존 이동 환경 결과와 섞지 않는다.

결과 경로: static_reward_1128/results_policy_comparison/<실행시간>/
summary.csv: 평균/표준편차 및 최소/최대
runs.csv: 세 방식 x 10회, 전체 30개 결과
comparison.fig/png: 4개 평가 지표 그래프, 오차막대는 표준편차
quadratic_training.csv: 100회 학습 기록
quadratic_agent_0100.mat: 최종 학습 신경망
각 정책/repeat_01~10: 전체 패킷/위성 선택/연속 손실/배치/신호 로그
study.mat: 다시 열기용 결과 데이터
VERIFICATION.txt: 전체 패킷과 동일 평가 조건 검증 결과
