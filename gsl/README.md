# LEO GSL Simulator for Real-Time UDP Traffic

## Research context

명지대학교 정보통신공학전공 캡스톤 연구 주제는 **“실시간 UDP 트래픽을 위한 강화학습 기반 LEO 위성 라우팅 – 지연·패킷 손실 최소화”**입니다. 이 폴더는 전체 연구 중 **MATLAB 기반 Ground–Satellite Link(GSL)** 부분입니다.

Ground User → Serving LEO Satellite → **future Python ISL simulator** → Destination GSL

현재는 GSL 기하·참조 downlink 상태·패킷 단위 시뮬레이션을 구현합니다. 실제 UDP 소켓, ISL 라우팅, RL은 구현 범위에 포함하지 않습니다. 상위 구조의 Ground User 화살표와 별개로 RF 수치는 **Ku-band DOWNLINK 참조값**입니다. 실제 uplink 성능으로 해석하지 않습니다.

## Ground Station

기본 CONFIG는 **위도 37.0000°N, 경도 128.0000°E, 고도 0 m(WGS84 타원체 기준)**입니다. 임시 연구 예시 좌표이며 캠퍼스/실제 측량 지점을 뜻하지 않습니다. 이번 시각화 수정에서 좌표는 변경하지 않았습니다.

`configGSL.m`의 `gsLatitude_deg / gsLongitude_deg / gsAltitude_m`를 수정할 수 있습니다. 실제 실행값은 시작/최종 요약, Figure 부제, MAT의 CFG에서 확인합니다.

## Current main assumptions

| 항목 | 설정 |
|---|---|
| Orbit | 이상화한 원형 Walker-Delta, two-body-keplerian |
| Altitude / inclination | 550 km / 53° |
| Constellation | 72면 × 22기 = 1,584기, phaseFactor F=39 |
| Minimum elevation | 25° |
| Serving | 가시 후보 중 최고 elevation, 기존 위성 대비 **4° 초과**일 때 전환 |
| Forced switch | 기존 serving이 안 보이면 가시 후보로 전환 |
| RF reference | Ku-band downlink, 12 GHz, EIRP density 12.88 dBW/MHz, G/T 13.7 dB/K |
| Bandwidth assumption | 평탄한 PSD, 신호 대역폭=잡음 대역폭; 데이터율과 RF 대역폭을 혼동하지 않음 |
| Channel | Clear-sky/free-space 참조; 대기/강우/간섭/추가 pointing loss 없음 |
| Doppler | raw shift 계산, ideal compensation으로 residual=0 |
| UDP | 150 Bytes, 20 packets/s baseline, 60 packets/s stress |
| Time grid | 채널 1초 / 패킷 1/packetRate초; 기본 600초 |
| PER | 검증 곡선 미확보; arbitrary PER/loss/penalty 사용 안 함 |

550 km는 WGS84 적도반지름에 더해 정의한 궤도 반경입니다. F=39는 각도가 아니라 Walker 위상 인자이며 실제 Starlink TLE가 아닙니다. J2/항력/지형 가림은 모델링하지 않습니다.

## Visualization meaning — 3D satelliteScenarioViewer

- **노란 큰 marker + Ground Station 라벨**: GS.
- **초록 선**: 가시 candidate/available GSL. RF 수신 성공을 보장하지 않으며 동시 데이터 송신을 의미하지 않습니다.
- **빨간 굵은 선 + 빨간 위성 marker/라벨**: 현재 UDP 송신 시도에 사용하는 serving GSL 하나.
- 나머지 위성은 작은 중립색 marker입니다. Viewer 제목에 색의 의미, 현재 시각과 serving ID를 표시합니다.

요청한 **green dashed / red dashed**의 의미는 각각 candidate / active입니다. 그러나 **설치된 R2026a Access API에는 LineStyle이 없고 LineColor/LineWidth만 있습니다.** 따라서 실제 구현은 **초록 실선 / 빨간 굵은 실선**입니다. 존재하지 않는 속성을 사용하지 않습니다.

동일 access 객체의 색을 바꾸므로 serving에 초록/빨간 선이 중복되지 않습니다. 이전 serving은 초록으로 복귀하고 새 serving 하나만 빨간색이 됩니다. 후보가 없으면 active link도 없습니다.

`playGSL(R)`는 각 채널 시각과 링크 색을 순서대로 갱신합니다. 정확한 특정 시각 확인에는 `R.viewerController.setTime(476)`를 사용합니다. R2026a CurrentTime은 SetObservable이 아니며, timer로 native viewer 시간 이동과 색 갱신을 겹치면 이번 환경에서 그래픽 갱신 정지/비정상 종료가 관찰되어 background timer를 사용하지 않습니다.

**색 동기화 재생은 반드시 `playGSL(R)`를 사용하세요.** Native viewer Play 또는 `play(R.scenario)`는 궤도만 재생하며 빨간 serving 색을 자동 갱신하지 않습니다. Native 시간 이동을 끝낸 뒤에는 `R.viewerController.refresh()`로 색을 갱신할 수 있습니다. 프레임마다 native graphics 갱신을 기다리므로 실제 재생 속도는 PC 성능에 따라 설정한 10배속보다 느릴 수 있습니다. Controller를 삭제하면 소유한 viewer도 닫힙니다.

## Main outputs

현재 PER 미정 상태에서는 **3D viewer + 일반 Figure 3개**만 생성합니다.

1. **3D GSL Environment**: Earth, GS, 위성, candidate/serving 구분.
2. **GSL Serving Satellite and Handover**: 실제 serving elevation + 25° 선, serving ID, handover 점선.
3. **GSL Link Performance**: one-way propagation delay(ms), SNR(dB), 두 패널 모두 handover 점선.
4. **Cumulative UDP Packet Transmission**: Generated/Transmitted/Received/Lost 누적.
5. **Rolling Packet Loss Ratio**: 유효한 PER 기반 rolling 값이 있을 때만 별도 Figure. 기본 5초 이동 창.

위성 ID는 물리적 크기가 아닌 식별자이므로 **동일 간격의 범주 축에 실제 ID를 표시**합니다. 기존 476~489초 구간은 **ID=7**이었으며 0이 아니었습니다. 과거 0~1,500 숫자 축에서는 7이 0처럼 보였습니다. 선택 로직은 강제로 바꾸지 않았고, `candidate count>0 ⇒ serving ID>0`를 모든 시각에서 검증합니다. 실제 no-serving은 **0 (none)** 항목입니다.

최대 elevation, 임의 고정 위성 elevation, 후보 수/boolean, slant range, FSPL, ECEF 속도, radial velocity, transmission delay, raw Doppler는 메인 Figure에서 제외하고 내부 데이터/CSV/MAT에 유지합니다. 모든 위성의 elevation과 range는 geometry MAT에 보존합니다.

## Packet definitions and limitations

- **Generated**: application이 생성한 패킷 수.
- **Transmitted**: serving+visibility가 유효하여 송신을 시도한 패킷 수. outage에서는 generated만 증가할 수 있습니다.
- **Received**: 송신 후 PER 추첨에서 성공한 패킷.
- **Lost**: 송신 후 PER 추첨에서 손실된 패킷. 미송신 패킷과 구별합니다.

**현재 validated SNR→PER 모델이 없습니다. Received/Lost/PLR은 N/A이며 실제 연구 성능 결과로 사용할 수 없습니다.** 미정 송신 결과는 outcome_pending에 기록합니다. 가짜 0% loss 그래프나 handover/Elevation/Doppler에 따른 임의 손실은 만들지 않습니다.

PER가 준비되면 `CFG.perModel`과 `CFG.perModelSource`를 설정합니다. 자세한 프레임 길이·SNR 정의·적용 범위 요건은 [패킷 모델 설명](PACKET_LAYER.md)을 참고하세요.

PLR=Lost/Transmitted×100, PDR=Received/Transmitted×100. 분모가 0이거나 필요한 결과가 미정이면 NaN입니다. Rolling은 **(t−5초,t]**의 송신 패킷을 분모로 사용합니다. 판정이 완료되면 Lost+Received=Transmitted이며, 미정일 때는 resolved lost+resolved received+pending=transmitted입니다.

카운터는 송신 시각에 귀속된 최종 패킷 결과이며, 지연 후 도착 시각의 실제 수신 이벤트 곡선이 아닙니다. 큐·재전송·handover 중단 시간은 추가하지 않았습니다.

## Doppler / link budget

Raw Doppler는 ECEF LOS와 상대속도로 계산합니다. 접근 양수/이탈 음수이고 ideal compensation으로 residual=0입니다. 현재 packet loss에 직접 영향을 주지 않습니다.

`SNR = EIRP_density(dBW/MHz) − 60 + G/T − FSPL − 10log10(k) + 10log10(Bsignal/Bnoise)`

이는 C/N이며 Eb/N0가 아닙니다. RF 절대 대역폭을 데이터율 50 Mbps로 대신하지 않습니다. [공식 link-budget 근거](https://www.mathworks.com/help/satcom/gs/satellite-link-budget.html), [ECEF states 정의](https://www.mathworks.com/help/satcom/ref/matlabshared.satellitescenario.satellite.states.html), [Access 표시 속성](https://www.mathworks.com/help/satcom/ref/matlabshared.satellitescenario.access.html).

## MATLAB requirements and how to run

실제 실행 확인: **MATLAB R2026a Update 5 + Aerospace Toolbox 26.1**. 이번 코드 실행에 Simulink, Communications Toolbox, Satellite Communications Toolbox를 추가로 사용하지 않았습니다. Windows viewer 표시를 실제 확인합니다. 다른 버전의 호환성은 별도 검증이 필요합니다.

현재 폴더를 이 README와 .m 파일이 있는 곳으로 설정하세요.

```matlab
R = main_gsl_simulation;
playGSL(R);                         % 프레임 동기화 3D 재생
R.viewerController.setTime(476);    % serving ID 7 시각 확인
```

```matlab
CFG = configGSL();
CFG.packetRate_pps = CFG.stressPacketRate_pps; % 60 pps stress
CFG.outputDir = fullfile(pwd,'results_packets_stress');
R = main_gsl_simulation(CFG);
```

`CFG.openViewer=false`는 viewer를 끄고, `CFG.makePlots=false`는 일반 Figure를 끕니다. `CFG.debug=true`에서만 serving 선택 진단을 출력하고 serving_debug.csv를 저장합니다. 일반 실행에는 간결한 GS 정보와 최종 요약만 출력합니다.

## Output files

기본 `results_packets/`에 저장하며 같은 이름은 갱신됩니다.

| 파일 | 내용 |
|---|---|
| geometry_stage1.mat | 기존 CFG/G 형식 유지. 모든 위성 elevation/range/visibility 및 시작·끝 위치 |
| visibility_summary.csv | time_s, 후보 수/유무, constellation 최대 elevation, 기존 고정 예시 위성의 ID/elevation (보조 데이터) |
| satellite_index.csv | MATLAB 위성 배열 인덱스와 이름; NORAD ID가 아님 |
| link_state.csv | serving/handover/elevation, range/delay/FSPL/SNR, radial velocity/Doppler, ECEF 위성 속도, 후보 수/유무/최대 elevation |
| packet_results.csv | 패킷 상태, SNR/PER/delay, handover, pending, 누적/rolling 지표 |
| packet_results.mat | P/M/L/CFG; 패킷·link 상태 원본 |
| packet_summary.txt | GS 좌표를 포함한 최종 요약 |
| serving_handover.png | Figure 1 |
| link_performance.png | Figure 2 |
| cumulative_packets.png | Figure 3 |
| rolling_packet_loss.png | 유효한 rolling PER 결과가 있을 때만 |
| serving_debug.csv | debug=true일 때 선택 판단 이력 |
| serving_audit_470_492.csv | verify_visualization 실행 시 해당 구간 진단 |

이전 버전의 visibility.png/environment_3d.png/link_state.png와 PER 없는 rolling_packet_loss.png는 같은 결과 폴더에서 정리합니다. Python은 CSV 사용을 권장합니다. NaN/빈칸은 미정이며 0으로 채우지 마세요. 모든 time_s는 CFG.startTime UTC로부터의 초입니다.

## Verification

```matlab
verify_packets             % 카운터·rolling·hysteresis 경계조건
verify_packet_integration  % geometry + RF 단위 + CSV/MAT
verify_visualization      % viewer 색 전환/GS/3 Figure/ID=7/invariant
```

600초/20pps=12,000개, 60pps=36,000개를 검증합니다. 기본 시나리오는 handover 10회, 후보 9~13기, serving=0 구간 없음입니다. 기본 PER가 없으므로 수신/손실 성능은 아직 미정입니다. 검증 로그는 validation_visualization.log 및 기존 validation_packets*.log에 있습니다. 소프트웨어 테스트용 PER=0/1 값은 연구 결과로 내보내지 않습니다.

## Future work

- 검증된 SNR→PER 모델과 패킷/코드블록 매핑
- GSL → Python ISL 연동
- E2E delay / jitter / deadline miss
- RL routing

이전 버전은 Git 이력에서 확인하며 현재 실행 파일명과 경로는 유지합니다.
