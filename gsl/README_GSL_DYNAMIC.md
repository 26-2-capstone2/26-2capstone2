# 위성 수 변경과 랜덤 SNR 실험

환경감쇠는 8 dB를 유지한다. 위성 수를 바꾸어 실행하려면 MATLAB 현재 폴더를 gsl로 맞추고 다음처럼 실행한다.

~~~matlab
CFG = configGSL();
CFG.numPlanes = 30;       % 궤도면 수
CFG.satsPerPlane = 30;    % 면당 위성 수. 전체 900개
R = main_gsl_simulation(CFG);
~~~

전체 위성 수는 numPlanes × satsPerPlane으로 계산한다. 기본 설정은 30 × 30 = 900개다. 예를 들어 20 × 40은 800개, 40 × 40은 1,600개다. configGSL.m에서 두 값을 바꿔 저장하면 일반 시뮬레이션과 강화학습 모두 같은 배열 설정을 사용한다.

위성 수는 환경을 생성할 때 정하며, 바꾸면 새 환경을 생성한다. 위성이 줄면 연결 가능한 위성이 없는 구간이 생길 수 있으며, 해당 구간은 연결 불가 손실로 처리한다. 실행 가능한 최대 개수는 PC 메모리와 계산 시간에 따라 달라진다.

## 랜덤 SNR

이전에도 거리 변화에 따라 SNR이 바뀌었다. 이번에는 그 값에 위성별로 독립적인 랜덤 변동을 추가한다.

SNR = 거리 기반 링크 버짓 SNR - 환경감쇠 8 dB + 위성별 랜덤 변동

기본 설정은 다음과 같다. 실측 날씨 모델로 보정한 값이 아니라 환경 변화에 대한 학습 정책 평가용 가정이다.

- snrRandomStd_dB = 1. 위성별 가우시안 변동의 표준편차 1 dB.
- snrCorrelation_s = 5. 직전 값과 이어지는 변동을 만들기 위한 상관시간 5초.
- snrRandomSeed = 20261115. 같은 시드이면 같은 궤도·같은 위성 수에서 같은 값 재현.
- snrRandomStd_dB = 0으로 설정하면 랜덤 변동을 끄고 거리 기반 SNR을 사용.

후보 Table의 snr_dB, snrChange_dB, 실제 패킷의 snr_dB와 PHY 오류 계산에 동일한 SNR을 사용한다. snrRandomOffset_dB에서 추가된 변동을 확인할 수 있다. 후보 SNR은 매초 갱신되며 그 1초 동안 발생한 60개 패킷에 같은 링크 값을 적용한다.

## 강화학습 환경에서 사용

~~~matlab
CFG = configGSL();
CFG.numPlanes = 30;       % 궤도면 수
CFG.satsPerPlane = 30;    % 면당 위성 수. 전체 900개
CFG.snrRandomStd_dB = 1;
env = GSLRLEnvironment([], CFG);
candidates = env.reset();
openvar('candidates')
allVisible = env.allCandidates();
state = env.observe();
[candidates, feedback, done, packets] = env.step(1);
~~~

후보가 없으면 action=0을 사용한다. reset(packetSeed,snrSeed)로 패킷과 SNR의 시드를 따로 정할 수 있다. reset(packetSeed)만 호출하면 SNR은 설정의 snrRandomSeed를 사용한다.

기본 candidateCapacity=13을 유지해 위성 수가 달라도 입력 79개·출력 13개를 유지한다. 후보가 적으면 빈 칸을 0으로 채우고 선택을 막는다. 13개보다 많으면 SNR 상위 후보를 제공하며, 현재 연결 위성이 여전히 보이면 상위 후보 밖에 있어도 가장 낮은 슬롯을 대체해 유지 선택을 허용한다. 제공된 후보는 다시 SNR 순으로 정렬한다.

allCandidates()는 슬롯 제한 없이 현재 보이는 위성 전체를 반환한다. stepSatelliteID(id)는 현재 보이는 실제 위성 ID로 직접 연결한다. 기존 방식과 최고 SNR 비교 방식은 전체 후보를 사용한다.

학습된 모델을 재사용할 때 candidateCapacity와 State 열의 의미를 유지해야 한다. 후보 용량을 바꾸면 신경망 크기도 달라져 새로 학습해야 한다. 위성 수와 SNR을 바꾸어 평가할 수 있다는 것은 성능 유지가 검증되었다는 뜻과 구별한다.

## 학습과 평가 설정

~~~matlab
O = configGSLDQN();
O.environmentConfig.numPlanes = 30;
O.environmentConfig.satsPerPlane = 30;
O.environmentConfig.snrRandomStd_dB = 1;
R = train_gsl_ddqn(O);
~~~

학습·평가 함수는 각 패킷 시드에 설정의 snrRandomSeed를 더해 별도 SNR 시드를 만든다. 같은 평가 시드에서 세 방식은 같은 위성별 SNR 변동과 같은 원본 패킷 난수를 사용한다. 모델과 함께 O.environmentConfig도 저장한다.

verify_gsl_dynamic으로 위성 수 1·73·1000개, 빈 후보, 고정 슬롯, 같은 시드 재현, 다른 시드 변화, 후보 SNR과 실제 패킷 SNR 일치를 확인한다. verify_gsl_rl은 랜덤 변동을 0으로 두고 과거 기준 결과를 재현한다.

일반 MATLAB 화면은 main_gsl_simulation.m, Double DQN 학습은 train_gsl_ddqn.m을 실행한다.
