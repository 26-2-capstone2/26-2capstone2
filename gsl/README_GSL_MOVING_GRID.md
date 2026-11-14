# 실험용 함께 이동하는 6×11 격자

## 확인한 ISL 코드

ISL-MATLAB의 config_isl.m과 ISL-Python의 config_isl.py는 6×6 가상 격자와 상하 7 ms·좌우 2 ms 링크 지연을 정의한다. 가까운 위성 무리의 실제 간격이나 시간별 이동 좌표는 정의하지 않는다.

RL 브랜치 sim/topology.py의 iridium은 전 지구 궤도 배치를 정지 상태로 근사한다. 여기의 780 km·86.4도·31.6도는 가까운 격자의 200/400 km 간격을 제공하는 설정이 아니다.

이번에는 사용자가 선택한 연구용 가정에 따라 새로운 이동 좌표를 만들었다. 위성 (p,s) 번호와 상하좌우 연결 규칙은 ISL 기본 grid 모드를 따른다. ISL에서 같은 크기를 사용하려면 grid:6x11로 설정한다.

## 새 가정

| 항목 | 설정 |
| --- | --- |
| 격자 크기 | 6×11 = 66개 |
| p 이웃 방향 기준 구면 간격 | 200 km |
| s 이웃 방향 기준 구면 간격 | 400 km |
| 기준 구면 고도 | 780 km |
| 격자 중심 속도 | ECEF 기준 7.5 km/s |
| 진행 방향 | 동쪽. heading=90도 |
| 중심 통과 시각 | 실행 중간. 기본 600초 실행에서는 300초 |
| 환경감쇠 | 8 dB |
| 위성별 랜덤 SNR | 표준편차 1 dB, 상관시간 5초 |

격자 전체에 공통 회전을 적용하므로 위성 사이 3차원 직선거리가 시간에 따라 유지된다. 기준 구면의 간격을 입력하므로 실제 이웃 직선거리와는 곡률에 따른 작은 차이가 있다. 실제 거리는 공유 CSV에 기록한다.

이 모델은 실험용 운동학 모델이다. 실제 이리듐 위성들이 이 간격으로 모여 운용된다는 의미로 사용하지 않는다. 개별 위성의 자연적인 케플러 궤도와 편대 유지 제어를 검증하는 모델은 별도 연구 범위다.

## 설정과 실행

configGSL.m에서 변경한다.

~~~matlab
CFG.constellationType = 'moving_grid';
CFG.numPlanes = 6;
CFG.satsPerPlane = 11;
CFG.gridCrossSpacing_m = 200e3;
CFG.gridAlongSpacing_m = 400e3;
CFG.gridCenterSpeed_mps = 7500;
CFG.gridHeading_deg = 90;
CFG.gridPassTime_s = []; % 자동으로 실행 시간 중간. 숫자를 넣으면 초 단위로 지정
~~~

main_gsl_simulation.m을 실행하면 결과·진단 화면에 더해 GSL Moving Grid Layout 창이 열린다. 0초·중간·마지막의 격자 배치를 같은 기준 좌표에서 비교한다. 지구본을 사용하지 않는다.

train_gsl_ddqn.m도 같은 설정을 읽는다. 입력 79개·출력 13개를 유지하며, 후보가 13개보다 많을 때는 기존 상위 SNR 후보와 현재 연결 위성 유지 규칙을 사용한다.

## ISL에 전달할 공통 파일

기본 결과 폴더에 다음을 저장한다.

- shared_grid_positions.csv. 매초 각 위성의 ECEF 위치·속도, (p,s), 위성 ID, 고도각과 가시성.
- shared_grid_links.csv. 상하좌우 이웃, 링크 번호, 실제 직선거리와 거리/빛의 속도, 기존 ISL 가상 지연을 별도 열로 기록.
- shared_grid_contract.json. 좌표계·단위·번호 계산식·운동 가정.
- isl_input_packets.csv. GSL 수신 패킷의 원본 ID·생성 시각·위성 도착 시각·목적지 위성 ID와 p,s.

위성 ID는 p*satsPerPlane+s+1이다. p,s는 0부터 시작한다. ISL 링크 ID는 Python build_grid.py와 동일한 열 우선 순서이며 p+numPlanes*s+numPlanes*satsPerPlane*(direction-1)로 계산한다. 방향은 1=상(s-1), 2=하(s+1), 3=좌(p-1), 4=우(p+1)다.

6×11 열린 격자는 유효한 방향 링크 230개가 있다. 양쪽 끝을 서로 연결하는 wrap은 사용하지 않는다.

ISL의 기존 7/2 ms 가상 지연과 새 좌표에서 계산한 전파 지연은 서로 다른 값이다. 완전한 통합에서는 ISL이 이 공유 좌표·링크 지연과 패킷별 진입 p,s를 읽도록 연결해야 한다. 이번 GSL 구현은 해당 인터페이스 파일을 생성하며, 팀원 ISL 브랜치의 실행 코드는 수정하지 않았다.

## 검증 결과

verify_gsl_moving_grid에서 600초 동안 격자 간격 유지, 구면 반경, 66개 위성 이동, 링크 230개와 번호 대응, 공통 좌표 및 패킷 파일, 일반 GSL과 강화학습 환경의 패킷별 결과 일치를 확인한다.

현재 기본 가정의 한 시드에서 연결 후보는 18~42개였고 연결 불가 시간은 0초였다. 기존 고도각 선택은 손실률 94.2361%, 최고 SNR 매초 선택은 85.3222%였다. 이 값은 기존 8 dB 링크 버짓과 PHY 근사를 유지한 결과이며, 학습한 Double DQN 성능으로 해석하지 않는다.

후보 선택을 연구할 수 있는 격자 이동을 구현한 결과와 실제 위성망의 물리 검증을 구별한다.

## 참고한 저장소

- https://github.com/26-2-capstone2/26-2capstone2/blob/ISL-MATLAB/isl_6x6_routing/config_isl.m
- https://github.com/26-2-capstone2/26-2capstone2/blob/RL/isl_routing/sim/build_grid.py
- https://github.com/26-2-capstone2/26-2capstone2/blob/RL/isl_routing/sim/topology.py
