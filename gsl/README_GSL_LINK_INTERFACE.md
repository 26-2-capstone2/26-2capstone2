# GSL 위성 상태 조회와 실제 위성 ID 연동

## 전체 위성 상태 보기

~~~matlab
env = GSLRLEnvironment();
env.reset();
T = env.allSatelliteStates();
openvar('T')
~~~

현재 시점의 위성 66개 전체를 반환한다.

| 열 | 의미 |
| --- | --- |
| time_s | 현재 결정 시각 |
| satelliteID | 1부터 시작하는 고정 위성 ID |
| p, s | ISL의 0부터 시작하는 격자 좌표 |
| snr_dB | 환경감쇠와 위성별 랜덤 변동을 반영한 SNR |
| elevation_deg, slantRange_m | 고도각과 지상국까지 거리 |
| isVisible | 최소 고도각 조건을 만족하는지 |
| inActionSet | 현재 DDQN의 고정 슬롯에 들어온 후보인지 |
| isServing | 직전 결정에서 선택한 위성 ID인지 |

보이지 않는 위성은 isVisible=false와 snr_dB=NaN으로 표시한다. 이 NaN은 가시성 때문에 연결 후보에서 제외한 표시다. isServing은 직전 선택 기록이므로 위성이 시야를 벗어나면 isVisible=false와 동시에 나타날 수 있다.

env.allCandidates()는 현재 보이는 모든 후보를 반환한다. env.observe()는 현재 13개 슬롯에 대한 신경망 입력과 actionMask, satelliteIDs를 반환한다. 종료 시각에 도달하면 상태 Table과 다음 후보는 비어 있고 done=true다.

## 실제 위성 ID를 GSL에 반영하기

~~~matlab
T = env.allSatelliteStates();
visible = T(T.isVisible,:);
selectedID = visible.satelliteID(1);
[nextCandidates, feedback, done, packets] = env.stepSatelliteID(selectedID);
~~~

selectedID를 현재 보이는 위성 ID와 대조해 연결한다. 보이지 않거나 존재하지 않는 ID는 오류로 거부하며 시간을 진행시키지 않는다. 후보가 전혀 없을 때는 0을 전달한다.

같은 위성 ID면 연결을 유지한다. 다른 ID로 직접 바뀌면 100 ms 핸드오버 중단을 적용한다. 첫 연결, 연결 불가, 단절 이후 재연결의 정의는 기존 코드의 기준을 따른다.

feedback의 previousServingSatID, servingSatID, handover, handoverInterruption_s에서 전환 결과를 확인한다. packets의 destinationSatelliteID, snr_dB, lossCause, handover_loss, onTime, latency_ms에서 패킷별 결과를 확인한다. 1초 동안 처리한 결과와 다음 시각 후보를 함께 반환한다.

env.step(rank)는 후보 순위를 받는다. env.stepSatelliteID(id)는 실제 위성 ID를 받는다. 순위와 ID의 값이 같다고 가정해서 연결하지 않는다.

## Double DQN 연결

프로젝트의 GSLDoubleDQN.select는 현재 후보 순위를 반환한다. selectGSLDDQNSatelliteID가 observation.satelliteIDs를 이용해 실제 위성 ID로 바꾼다.

~~~matlab
S = load(fullfile('results_ddqn','20261112_163509_823','agent.mat'),'agent');
policy = @(observation,allSatellites) selectGSLDDQNSatelliteID(S.agent,observation);
R = main_gsl_link_interface(policy);
~~~

팀원 모델이 이미 실제 위성 ID를 반환한다면 해당 모델 호출을 policy 함수에 넣으면 된다. policy는 observation과 전체 위성 Table을 입력으로 받고 실제 위성 ID 하나를 반환한다.

0.1 dB 히스테리시스를 사용할 경우 policy에서 모델의 선택과 현재 위성의 SNR을 비교한 뒤 최종 ID를 반환한다. 환경은 반환된 ID를 실제 연결에 반영한다. 팀원 실험에서 사용한 히스테리시스 규칙을 policy에 연결해야 같은 방식을 평가할 수 있다.

## 연동 예제 실행

main_gsl_link_interface.m을 열고 F5를 누르면 최고 SNR 위성 ID를 선택하는 예제로 600초 동안 실행한다. 기본 예제는 신경망을 학습하거나 학습된 모델을 자동으로 불러오는 실행으로 정의하지 않는다.

반환값 R.initialSatelliteStates와 R.satelliteStates에서 최초 및 전체 시간의 상태를, R.decisions에서 매초 요청이 반영된 위성과 핸드오버를 확인한다. 결과 저장이 켜져 있으면 설정된 결과 폴더 아래 id_policy_interface에 다음을 기록한다.

- all_satellite_states.csv. 매초 모든 위성의 SNR·가시성·슬롯·연결 여부.
- id_policy_decisions.csv. 매초 실제 위성 ID·핸드오버·패킷 결과·보상.
- packet_results.csv 및 packet_results.mat. 원본 패킷 번호와 수신·손실·지연 기록.
- isl_input_packets.csv. GSL 수신 패킷과 ISL 진입 좌표 p,s.
- 기존 손실률·기한 내 도착률·연속 손실 요약.

## 검증 범위

verify_gsl_link_interface는 전체 상태와 후보 SNR 일치, 실제 ID 선택, 동일 ID 유지, 잘못된 ID 거부, 100 ms 중단에 따른 6개 패킷 손실, DDQN 후보 순위에서 ID 변환, 후보가 없는 경우와 600초 전체 기록을 확인한다.

새로운 이동 격자에서 기존 모델의 성능이 유지되는지는 별도 평가 대상이다. 이번 검증은 입력을 읽고 선택한 위성이 실제 GSL 링크에 반영되는지를 확인한다.

로컬에 내려받은 results_ddqn/20261112_163509_823/agent.mat도 2초짜리 별도 실행에서 확인했다. 실제 모델의 위성 ID 40 → 28 선택과 두 번째 결정의 핸드오버가 반영됐다. 이는 모델 파일 호환성과 ID 반영 검증이며 600초 성능 평가로 해석하지 않는다.
