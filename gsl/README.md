# GSL continuous UDP session simulator

> The objective is not to evaluate individual satellites independently.
> The simulator evaluates a continuous real-time UDP session in which
> the ground station communicates through the currently selected serving
> satellite and performs handovers as the LEO constellation moves.

## 실행

MATLAB R2026a + Aerospace Toolbox에서 이 폴더를 Current Folder로 열고:

```matlab
R = main_gsl_simulation;
```

실행하면 분석 결과와 3D 화면을 준비한 뒤 **0초에서 대기**한다. **GSL Session / Handover 창 하단의 ▶ 재생 / 이어서 (600초)** 버튼을 누르면 0~600초의 위성 이동과 현재 연결 위성을 함께 재생한다. 일시정지 후 같은 재생 버튼으로 이어서 볼 수 있으며, 끝난 뒤 재생하면 처음부터 다시 시작한다. 자동으로 프레임을 순회하거나 별도 화면을 반복해서 열지 않는다.

기본 결과는 results_packets에 덮어쓴다. 위치와 serving 색상은 같은 scenario advance 루프에서 갱신한다. 현재 연결 위성 하나만 빨강이며 이전 연결 위성은 회색 점으로 돌아간다. Native viewer의 재생 컨트롤 대신 위 버튼을 사용한다. 기존에 열린 이전 버전 3D 창은 닫고 main_gsl_simulation을 다시 실행한다. CFG.autoPlay3D는 기본 false이며 자동 재생은 명시적으로 true를 설정한 경우에만 사용한다.

**현재 연구 결과의 한계:** noise bandwidth와 50 Mbps의 information/coded rate 해석이 확인되지 않아 기본 PHY 결과는 미정이다. 기본 설정은 이 두 값이 NaN이며, 수신/전체 손실/전체 PLR을 0 또는 성공으로 꾸미지 않는다. 핸드오버 및 outage 손실은 확정적으로 계산한다. 실제 OS UDP socket 전송이나 실측 packet capture가 아닌 packet-event 시뮬레이션이다.

## 유지한 환경

| 항목 | 값 |
|---|---|
| Walker Delta constellation | 72 planes × 22 = 1584; F=39; 550 km; 53° |
| Ground Station | 37.0000 N, 128.0000 E; WGS84 altitude 0 m |
| Geometry update / duration | 1 s / 600 s |
| Elevation mask / hysteresis | 25° / strictly greater than 4° |
| Downlink | 12 GHz; EIRP density 12.88 dBW/MHz; G/T 13.7 dB/K |
| Link rate | 50 Mbps; rate interpretation for Eb/N0 remains TODO |
| UDP | 160 Bytes (1280 bits), 60 packets/s |
| PHY | QPSK + CCSDS AR4JA rate 1/2, information k=1024 bits |
| Handover interruption | 0.100 s per actual algorithm event |
| Channel | Clear sky, no interference; SNR C/N, not SINR |
| Doppler | ECEF range-rate raw Doppler; ideal compensation, residual 0 |

Signal PSD is flat and occupied signal/noise bandwidth ratio is explicitly 1 for the existing density-based C/N calculation. This ratio does not determine the absolute receiver bandwidth. Atmospheric, interference, pointing and Doppler penalties are not added.

## Serving selection / runtime 3D

각 시점 elevation >=25° 후보 중 최고 고도 위성을 찾는다. Serving이 없거나 기존 위성이 후보에서 벗어나면 즉시 후보를 선택한다. 기존 위성이 후보일 때는 bestElevation > currentElevation +4°에서만 전환한다. 후보가 있으면 serving ID는 반드시 0보다 크다. 최초 접속/접속 소실은 handover 수에 포함하지 않는다.

GSLManualViewerController와 playGSL은 실제 scenario advance와 graphic object를 같은 loop에서 갱신한다. viewer CurrentTime과 scenario SimulationTime의 일치도 검증한다. 이전 serving marker는 기본 회색으로, 기존 access는 녹색으로 복구한다. 새 serving marker/access는 빨강이며 access object를 추가 생성하지 않는다. Access는 시간에 따른 실제 visibility에 따라 표시된다. GS는 노란 큰 marker/label이다. 동시에 빨간 serving은 최대 하나이다.

R2026a의 Access 공개 API는 LineColor/LineWidth를 지원하지만 LineStyle은 없다. 따라서 candidate/serving access는 **녹색/빨간 실선**을 사용한다. Figure의 handover 시점 선은 점선이다.

## 연속 세션 / 손실 정의

Packet ID 1..36000, timestamp (ID-1)/60, [0,600)에서 계속 생성한다. Serving ID가 바뀌어도 traffic이나 RNG를 재시작하지 않는다. Packet timestamp에는 가장 최근 1 s geometry/channel 상태를 적용한다. 결과는 생성 시점에 귀속하며 수신 도착 시간을 별도로 모델링하지 않는다.

| 상태 | 정의 |
|---|---|
| Generated | Serving/outage와 무관하게 생성된 모든 packet |
| Received / SUCCESS | PHY까지 도달하고 오류 없이 전달된 packet |
| Lost | PHY + HANDOVER + OUTAGE, 중복 없음 |
| OUTAGE_LOSS | Serving 없음; 가장 먼저 적용 |
| HANDOVER_LOSS | Serving 있음, 실제 handover의 [tH,tH+0.100) 안에 생성 |
| PHY_LOSS | 앞 두 원인에 해당하지 않고 AR4JA packet error 발생 |
| UNRESOLVED_PHY | 대역폭/정보 비트율 미정 또는 published curve 범위 밖; 성공/손실 미정 |

요청한 네 최종 상태는 PHY가 평가 가능할 때 사용한다. TODO가 남은 packet은 거짓 최종 판정을 피하기 위해 UNRESOLVED_PHY 상태를 별도로 유지하며 received/lost/phyPER에는 NaN을 쓴다. Generated = confirmed received + confirmed lost + unresolved가 항상 성립한다. 한 packet은 정확히 한 상태만 갖는다. 미정이 하나라도 있으면 전체 Received/Lost/PHY loss/PLR은 N/A이다. Confirmed loss lower bound는 확정 손실/Generated이며 전체 PLR이 아니다.

5 s rolling window는 (t-5,t]이며 PLR = Lost/Generated ×100이다. Startup throughput은 실제 경과 구간만 분모로 쓴다. 미정 packet이 포함된 window의 전체 PLR/received pps는 N/A이다. 15 s마다 강제 전환하거나 handover당 6개를 강제로 drop하지 않는다. 소수점 표현 오차만 보정해 timestamp의 half-open 구간을 판정한다.

## 연구 기반 PHY

getPERfromSNR는 C/N을 **information Eb/N0**로 변환한다:

Eb/N0 [dB] = SNR C/N [dB] + 10 log10(noiseBandwidth_Hz / informationBitRate_bps).

JPL Figure 14의 rate 1/2, k=1024 CWER dashed curve를 PDF vector 좌표에서 읽었다. 데이터/재현 방법은 [AR4JA_CURVE.md](AR4JA_CURVE.md), [ar4ja_r12_k1024_cwer.csv](ar4ja_r12_k1024_cwer.csv)에 있다. Gray QPSK AWGN의 해당 coded curve를 사용한다. 기존 uncoded BER 공식/임의 threshold/sigmoid는 사용하지 않는다.

1280-bit packet을 ceil(1280/1024)=2개의 information codeword로 근사한다. **Codeword errors are independent**라고 가정하여 phyPER = 1-(1-pCW)^2. 마지막 block padding 및 실제 IP/L2 framing은 단순화한다. 확률 판정은 고정 seed의 private RandStream을 사용한다.

Lookup은 log10(CWER) 선형 보간이며 약 0..2.200262 dB 범위에만 유효하다. 범위 밖을 0/1로 clamp하거나 extrapolate하지 않는다. 높은 Eb/N0도 논문의 범위를 벗어나면 미정이다. 논문 plot digitization은 원시 Monte Carlo 표본을 대체하지 않으며 decoder 조건 차이를 검증해야 한다.

**TODO:** 근거가 있는 수신 noise bandwidth, 50 Mbps information/coded rate 해석을 확보한 뒤 configGSL의 noiseBandwidth_Hz/informationBitRate_bps/phyMappingSource를 설정한다. Test fixture의 50 MHz 값은 단위 테스트 전용이며 연구 실행에는 적용되지 않는다. Curve 밖 영역은 추가 decoder simulation/원본 자료 없이는 채우지 않는다.

## 선행연구

1. [Weather-Conscious Adaptive Modulation and Coding Scheme for Satellite-Related Ubiquitous Networking and Computing, Electronics 2022](https://www.mdpi.com/2079-9292/11/9/1297): Table 2의 constellation/RF/QPSK/AR4JA 환경 및 §5.1.2. Table에는 50 Mbps, 본문에는 100 Mbps가 있어 rate를 임의 재해석하지 않았다. §3.1의 bandwidth 기호에는 수치가 제시되지 않는다. 해당 논문의 SNR 식을 C/N↔Eb/N0 변환으로 그대로 간주하지 않는다.
2. [Jon Hamkins, JPL IPN 42-184 (2011), Performance of Low-Density Parity-Check Coded Modulation](https://ipnpr.jpl.nasa.gov/progress_report/42-184/184D.pdf): §VI.A, Figure 14, PDF page 30. Rate 1/2 / information k=1024 / AWGN coded QPSK reference.
3. [StarTCP: Handover-aware Transport Protocol for Starlink, APNet 2024](https://www.cuiyong.net/lunwen/2024/StarTCP_Handover-aware_Transport_Protocol_for_Starlink.pdf): §3의 100 ms simulation interruption. 이 프로젝트는 그 duration만 사용하고 paper의 15 s switching은 적용하지 않는다. Highest elevation +4° hysteresis는 본 프로젝트의 선택 정책이며 실제 Starlink scheduling 재현이라고 주장하지 않는다.

## 결과 / 검증

메인 Figure는 **GSL Session / Handover** (Serving ID/elevation + event 선)와 **UDP SESSION PERFORMANCE** (cumulative Generated/Received/Lost, 5 s rolling PLR, received pps) 두 개다. 미정 PHY에서는 확정 손실 lower bound를 점선으로 추가하고 실제 세션 KPI는 N/A로 표시한다. 개별 위성 성능은 메인 KPI가 아니다.

packet_results.csv/.mat에 요청한 camelCase packet 필드와 호환 snake_case 필드, RF/geometry 보조 변수를 저장한다. link_state.csv, geometry_stage1.mat, visibility_summary.csv, satellite_index.csv, packet_summary.txt, 두 PNG도 저장한다. results_packets_stress는 동일 60 pps 설정을 별도 재실행한 결과이며 스트레스 비교 연구라고 해석하지 않는다.

```matlab
verify_main_playback_entry; % t=0 wait + actual Play button callback
verify_handover_playback;    % opt-in automatic test for real position/color synchronization
verify_session;              % current full validation and both result folders
verify_packets;              % curve/units/strict hysteresis/loss priority/boundaries
verify_packet_integration;   % actual 1584 satellite, CSV/MAT, Doppler/SNR/accounting
verify_visualization;        % actual 3D handovers + real no-visible/outage case
```

이번 버전의 실행 증거는 validation_udp_session.log와 validation_session_packets.log이다. 과거 로그와 그래프가 있더라도 현재 코드의 연구 결과로 인용하지 않는다. 기본 정상 기하 시나리오: Generated 36000, actual handovers 10, known handover loss 60, outage 0, unresolved PHY 35940. Received/total Lost/overall PLR은 N/A이다.

## 이번 수정 파일

configGSL.m, selectServingSatellite.m, getPERfromSNR.m, simulatePacketTransmission.m, computePacketMetrics.m, reportPacketResults.m, plotResults.m, GSLViewerController.m, attachGSLPlaybackControls.m, verify_packets.m, verify_packet_integration.m, verify_visualization.m을 수정했다. verify_session.m, ar4ja_r12_k1024_cwer.csv, digitize_ar4ja_curve.py, AR4JA_CURVE.md를 추가했다. README.md/PACKET_LAYER.md와 저장소 root README, 현재 검증 로그 및 결과 폴더를 갱신했다.

## 재생 버그 수정

Native viewer 위치 재생과 serving 색상 갱신이 분리된 경로를 제거했다. 분석 후 scenario를 manual simulation으로 전환하고 advance마다 색상을 갱신한다. main 실행은 0초에서 대기하고 재생 버튼을 누르면 시작한다. 기존 위성은 회색 점/label off, 새 serving만 red marker/access이다. 공개 CurrentTime property는 SetObservable=false이므로 존재하지 않는 listener API나 background timer를 사용하지 않는다. 현재 버튼 실행 검증: validation_main_playback_entry.log. 핸드오버 색상 검증: validation_handover_playback.log.

실행 진입점은 동일한 main_gsl_simulation.m이며, 새 GSLManualViewerController를 사용해 기존 MATLAB 세션에 남은 이전 클래스 객체의 재생 경로를 재사용하지 않는다. Manual simulation API 근거: [MathWorks satelliteScenario/AutoSimulate](https://www.mathworks.com/help/satcom/ref/satellitescenario.html), [advance](https://www.mathworks.com/help/satcom/ref/satellitescenario.advance.html).

GSLViewerController.m은 호환용 이름이며 구현은 GSLManualViewerController.m 한 곳에 있다. 별도 자동 재생 검증에서 110 s 이동과 87/100 s 전환의 이전 회색/새 빨강/단일 빨강 검증을 통과했다.
