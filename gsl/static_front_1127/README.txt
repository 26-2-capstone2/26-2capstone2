정적 GSL 환경 + 시간에 따라 변하는 SNR (2026-11-27)

실행: gsl 폴더에서 main_gsl_static_simulation
저장된 결과를 바로 연다. 첫 실행에 저장 결과가 없으면 한 번 계산한다.
새 초기 배치: main_gsl_static_simulation('run',20279402)
같은 시드로 실행하면 같은 배치, SNR 변화, 패킷 난수가 재현된다.
설정: static_front_1127/configGSLStaticFront.m
검증: addpath('static_front_1127'); verify_gsl_static_front

600초 동안 위성 위치, 거리, 각도, 가시성은 고정된다.
6x11 격자 첫 열 근처가 GS 위에 놓인다. 격자 중심은 GS가 아니다.
초기 방향은 0~360도, 가로 오프셋은 +/-50km, 세로는 +/-100km 범위에서 무작위로 정한다.
각도는 좌표로부터 계산하며 서로 독립적인 난수로 배정하지 않는다.
간격은 기존 구면 격자의 기준 거리(200km,400km)를 유지한다.
SNR은 고정 거리의 링크 예산 + 위성별 시간 상관 Gaussian 변동으로 계산한다.
변동 표준편차 1dB, 상관 시간 5초, 갱신 간격 1초. 실측 보정한 채널은 아니다.
감쇠 6dB, Toolbox QPSK/AR4JA/AWGN PER 표 등 나머지 무선 조건은 유지한다.
실제 궤도 이동을 재현하는 모델이 아니라 위성 선택을 위한 정적 실험 환경이다.

환경 확인용 정책: MaxSNR + 0.1dB 히스테리시스. DDQN 재학습 결과가 아니다.
기존 이동 환경과 기존 학습 모델은 수정하지 않았다.
새 DDQN 학습에는 매 회차 createGSLStaticFrontEpisode(seed,C)를 호출해야 한다.
기존 main_gsl_simulation 및 기존 학습 실행 파일은 자동으로 새 환경으로 바뀌지 않는다.

검증 시드 20279401, 1회 결과:
보이는 후보 24개 / 전체 66개
생성 36000, 수신 33311, 손실 2689 (7.469444%)
최대 연속 손실 56개, 핸드오버 214회
이는 단일 배치/시드 결과로 기존 결과와 공정한 평균 성능 비교를 의미하지 않는다.

results_static_front/seed_<시드>/ 아래:
result.mat: 결과 재열기용 데이터
environment_and_results.fig, .png: 격자/SNR/각도/손실 그래프
static_satellites.csv: 초기 좌표, 각도, 가시성
initial_candidates.csv: 초기 후보 SNR 내림차순
candidates.csv: 모든 가시 후보의 초별 SNR, PER, 각도
packets.csv, decisions.csv, loss_runs.csv: 전체 패킷/선택/연속 손실 로그
isl_input.csv: 수신 성공 패킷의 ISL 인계용 CSV (실제 ISL 실행은 안 함)
satellite_id=p_zero_based*11+s_zero_based+1 (6x11 기준), p/s는 1부터 시작

정적 좌표/거리/각도, SNR 변화, 시드 재현성, 새 시드 초기 배치 변경,
20x20 및 36x36 생성, 패킷 손실 합계, 실제 핸드오버당 6개 손실 검증을 통과했다.
