# 이전 전 지구 Iridium 형태 GSL

현재 기본 실행은 [실험용 이동 격자](README_GSL_MOVING_GRID.md)를 사용한다. 아래 내용은 constellationType='iridium'인 이전 전 지구 배치에 대한 설명이다.

기본 위성 배치를 ISL의 RL 브랜치 isl_routing/sim/topology.py에 있는 iridium 프리셋에 맞췄다.

| 설정 | 값 |
| --- | --- |
| 궤도면 × 면당 위성 | 6 × 11 = 66개 |
| 고도 | ISL 구형 지구 반경 기준 780 km |
| 경사각 | 86.4도 |
| 이웃 궤도면 RAAN 간격 | 31.6도 |
| 같은 궤도면 위성 간 위상 간격 | 360/11도 |
| 면별 초기 위상 | 동일. ISL의 위도 근사와 대응 |
| 시간 | 600초 동안 1초 간격 이동 |

ISL은 지구 반경을 6,371 km로 사용하므로 궤도 반경을 6,371 + 780 = 7,151 km로 맞췄다. 지상국 위치 계산에는 기존 WGS84를 사용한다. 두 반경은 각각 orbitReferenceRadius_m과 earthEquatorialRadius_m으로 구분한다.

ISL 코드는 한 순간의 정지 배치와 위도별 링크 지연을 근사한다. GSL은 해당 초기 배치의 원형 궤도를 two-body-keplerian으로 전파한다. 시작 시각과 초기 RAAN은 프로젝트 설정값을 사용한다. 실제 운영 위성의 TLE를 재현하는 모델로 정의한 설정은 아니다.

ISL의 극지방 링크 제한과 첫째·마지막 궤도면 사이의 seam은 ISL 라우팅 조건이다. GSL에서는 지상국과 위성 사이의 고도각·SNR·핸드오버·패킷 전달을 계산한다.

## 실행

main_gsl_simulation.m을 열고 F5를 누른다. 기본으로 Iridium 형태 66개와 위성별 랜덤 SNR이 적용된다.

configGSL.m에서 다음 값을 확인할 수 있다.

~~~matlab
CFG.constellationType = 'iridium';
CFG.numPlanes = 6;
CFG.satsPerPlane = 11;
CFG.satAltitude_m = 780e3;
CFG.inclination_deg = 86.4;
CFG.iridiumPlaneSpacing_deg = 31.6;
CFG.phaseFactor = 0;
~~~

같은 배열을 사용하는 강화학습은 train_gsl_ddqn.m으로 실행한다. 입력·출력 슬롯은 기존 13개로 유지한다. 기존 학습 모델의 성능은 이 새 배치에서 별도로 평가해야 한다.

RF와 트래픽은 프로젝트의 실험 조건인 14 GHz, 환경감쇠 8 dB, 랜덤 SNR 표준편차 1 dB, 160 Bytes, 60 packets/s, GSL 기한 20 ms를 사용한다.

## ISL 위성 번호 대응

위성 ID는 1부터, ISL의 p와 s는 0부터 시작한다.

~~~matlab
satelliteID = p * CFG.satsPerPlane + s + 1;
~~~

- ID 1은 ISL (0,0).
- ID 11은 ISL (0,10).
- ID 12는 ISL (1,0).
- ID 61은 ISL (5,5).
- ID 66은 ISL (5,10).

후보 Table의 planeIndex와 satelliteInPlane에서 대응을 확인한다. 패킷 Table에는 destinationPlaneIndex와 destinationSatelliteInPlane을 저장한다. 연결 불가 패킷의 목적지 좌표는 NaN이다. satellite_index.csv에도 대응을 기록한다.

## 배열 크기 변경

numPlanes와 satsPerPlane으로 다른 크기도 구성할 수 있다. 기본 6개 면에서는 ISL 프리셋의 간격 31.6도를 사용한다. 6개가 아닌 면 수에서는 180도 범위에서 면을 균등 배치하는 일반화된 극궤도 모형을 사용한다.

기존 Walker Delta 배치를 다시 계산하려면 constellationType='walker_delta'와 원하는 고도·경사각·위성 배열·phaseFactor를 함께 지정한다.

## 검증

verify_gsl_iridium을 실행하면 위성 66개, 고도·경사각·RAAN 간격·위상 및 ISL 번호 대응을 확인한다. 600초 전체에서 일반 GSL과 강화학습 환경에 같은 위성 선택을 입력했을 때 패킷 결과가 일치하는지도 검사한다.

현재 기본 시각·고도각 25도·환경감쇠 8 dB의 600초 실행에서는 연결 불가 309초, 연결 불가 손실 18,540개, PHY 손실 17,460개로 전체 36,000개가 손실됐다. 이 결과는 구현 검증과 별도로 통신 조건을 새 궤도에서 평가해야 함을 보여준다.

원본 ISL 설정
https://github.com/26-2-capstone2/26-2capstone2/blob/a3a74f66622da23ecbcc0c350fd6f19c24a594ac/isl_routing/sim/topology.py
