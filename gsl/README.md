# LEO GSL Simulator for Real-Time UDP Traffic

명지대학교 정보통신공학전공 캡스톤 연구 **“실시간 UDP 트래픽을 위한 강화학습 기반 LEO 위성 라우팅 – 지연·패킷 손실 최소화”**의 MATLAB GSL 부분입니다.

Ground User → Serving LEO Satellite → future Python ISL simulator → Destination GSL

현재는 궤도/가시성/serving/handover, Ku-band downlink 참조 link state, 패킷 생성·송신 시도·수신/손실 시뮬레이션을 제공합니다. 실제 UDP 소켓이나 패킷 캡처 측정은 아닙니다.

## 실행

MATLAB Current Folder를 이 README와 .m 파일이 있는 기존 outputs/gsl 폴더로 설정하세요.

```matlab
R = main_gsl_simulation;
```

**Serving / Handover Summary Figure의 “Play / Resume 3D GSL” 버튼**으로 재생하고 “Stop” 버튼으로 정지합니다. 또는:

```matlab
playGSL(R);
R.viewerController.setTime(476);
```

재생은 현재 viewer 시각에서 이어지고, 끝에 도달했으면 처음부터 시작합니다. 색·시각 갱신을 순서대로 수행하므로 PC 성능에 따라 설정한 재생 배속보다 느릴 수 있습니다. Ctrl+C 또는 viewer 닫기로도 중단할 수 있습니다.

**Native viewer Play 및 play(R.scenario)는 serving 색을 자동 갱신하지 않습니다.** 이번 환경에서 native 시간 이동 중 background timer가 표시 속성을 바꾸면 그래픽 갱신 정지/비정상 종료가 관찰되어 timer를 쓰지 않습니다. 위 버튼 또는 playGSL을 사용하세요. Native 시간 이동을 완료한 뒤 R.viewerController.refresh()를 호출하면 현재 시각의 색을 갱신합니다.

## 기본 가정

| 항목 | 값 |
|---|---|
| 이상화한 Walker-Delta | 72 orbital planes × 22 = 1,584 satellites, F=39 |
| 궤도 | 550 km, inclination 53°, 원형 two-body-keplerian |
| GS | **37.0000°N, 128.0000°E, 0 m WGS84 타원체 고도** |
| Minimum elevation | 25° |
| Handover margin | 4° **이상(>=)** |
| RF 참조 | Ku-band DOWNLINK, 12 GHz, clear sky |
| EIRP density / G/T | 12.88 dBW/MHz / 13.7 dB/K |
| Signal/noise bandwidth ratio | 1, 평탄한 PSD |
| Packet reference noise bandwidth | **50 MHz**, 아래 BPSK 참조 모델을 위한 명시적 추가 가정 |
| Link gross bit rate | 50 Mbps |
| UDP | **160 Bytes, 60 packets/s**, 큐/재시도 없음 |
| Simulation | 600 s, channel update 1 s, rolling window 5 s |
| Doppler | raw shift 계산; ideal compensation, residual=0 |

GS는 임시 연구 예시 좌표이며 캠퍼스/측량 좌표가 아닙니다. 좌표는 이번 수정에서 변경하지 않았습니다. 550 km는 WGS84 적도반지름에 더한 궤도 반경이며 F=39는 Walker 위상 인자입니다. 실제 Starlink TLE, J2, 항력, 지형 가림, 강우, 간섭, 추가 pointing loss를 반영하지 않습니다.

## 연속 serving / handover

매 채널 시각에 elevation >= minimum인 위성만 후보입니다.

1. 기존 serving이 없거나 후보에서 벗어나면 최고 elevation 후보를 즉시 선택합니다.
2. 기존 serving이 후보이면 유지하되, **다른 최고 후보가 기존 elevation + margin 이상이면** 전환합니다.
3. 후보가 없으면 serving ID=0 (none), outage입니다.
4. 0→위성 획득과 위성→0 단절은 handover 수에 포함하지 않고 위성→다른 위성 전환만 셉니다.
5. 후보가 있으면 serving ID>0인지 매 실행 검증합니다. 동률은 가장 작은 MATLAB 배열 인덱스로 처리합니다.

기존 strict >4° 조건을 요청대로 >=4°로 변경했습니다. 이전 위성은 기본 회색 marker/초록 access로 복귀하고 새 위성 하나만 빨간 marker/access로 강조합니다. 기존 active access의 색을 바꾸므로 같은 위성에 초록·빨강 링크를 겹쳐 생성하지 않습니다.

## 3D 표시

- 노란 큰 GS marker + Ground Station 라벨.
- 초록 선: elevation 조건을 만족하는 가시 후보 GSL, 동시 UDP 전송을 뜻하지 않음.
- 빨간 굵은 선 + 빨간 위성 marker/라벨: 현재 송신 시도에 사용하는 serving 하나.
- 제목: 갱신한 시각, serving ID, 후보 수, 누적 handover 수, outage 여부.
- ID=0/outage이면 빨간 active 링크가 없습니다.

요청한 초록/빨간 **점선**에 대해 설치된 R2026a Access API를 확인했으나 공개 LineStyle 속성이 없습니다. 현재 지원되는 LineColor/LineWidth로 초록 실선과 빨간 굵은 실선을 구현합니다. 선의 실제 화면 패턴은 native renderer에 따릅니다.

## 패킷 성공 모델 — 명시적인 참조 모델

현재 기본 모델은 **ideal uncoded coherent BPSK over AWGN**입니다. 사용자 요청에 따라 미정 PER 상태에서 수신/손실 집계가 가능한 참조 모델을 추가했습니다. 실제 Starlink PHY/PER를 검증한 모델이나 실측 결과로 해석하면 안 됩니다.

`Eb/N0 = 10^(SNR_C/N_dB/10) × Bnoise / Rbit`

`BER = 0.5 × erfc(sqrt(Eb/N0))`

독립 bit 오류와 한 bit 오류만 있어도 packet 실패라는 가정에서:

`PER = 1 − (1−BER)^(8 × packetBytes)`

작은 BER에서도 수치가 보존되도록 log1p/expm1으로 계산합니다. [MathWorks erfc의 BPSK BER 예제](https://www.mathworks.com/help/matlab/ref/erfc.html)와 [uncoded AWGN 식](https://www.mathworks.com/help/comm/ug/analytical-expressions-used-in-berawgn-function-and-bit-error-rate-analysis-app.html)을 참고합니다. erfc는 기본 MATLAB 함수이며 Communications Toolbox 함수는 호출하지 않습니다.

**SNR=C/N을 Eb/N0로 무조건 동일시하지 않습니다.** Bnoise=50 MHz, Rbit=50 Mbps라는 참조 가정 때문에 기본값에서 두 선형 값의 비율이 1입니다. CFG.referenceNoiseBandwidth_Hz와 linkDataRate_bps를 수정하면 변환도 바뀝니다. 신호/잡음 RF 대역폭 비를 유지해야 합니다.

기본 시나리오의 SNR 약 24~26 dB는 이 이상적인 모델에서 BER/PER가 극히 작아 유한 표본에서 **손실 0**이 나올 수 있습니다. 이것은 가정한 참조 모델의 결과입니다. Handover penalty, 임의 SNR penalty, burst loss를 넣어 손실 그래프를 인위적으로 만들지 않습니다.

검증 곡선을 확보하면 CFG.perModel에 `@(snr) ...`를 넣고 CFG.perModelSource에 SNR 정의·프레임 길이·출처를 기록하세요. 비워두면 현재 크기/대역폭/속도로 BPSK 참조 모델을 계산합니다. 모델이 NaN을 반환하면 unresolved attempt로 보존하며 영향을 받는 수신/총손실/rolling 값은 N/A입니다.

## Packet accounting

패킷은 [0,T)에서 1/rate초마다 생성하며, 해당 채널 상태를 다음 채널 갱신까지 유지합니다. 같은 step에 생성되는 패킷마다 즉시 송신 여부를 결정합니다.

- **Generated**: application 생성.
- **Attempted / Transmitted**: 유효한 serving 링크에서 즉시 송신 시도. transmitted는 attempted의 호환 alias입니다.
- **Received**: PER 기반 추첨 성공.
- **Outage loss**: serving/링크가 없어 송신하지 못한 패킷.
- **Link loss**: 송신을 시도했으나 PER 기반 추첨 실패.
- **Lost**: outage loss + link loss.
- **Pending**: 송신은 시도했지만 PER가 미정인 결과.

`Generated = Attempted + OutageLoss`

`Attempted = Received + LinkLoss + Pending`

`Generated = Received + TotalLost + Pending` (resolved counts 기준)

**Overall failure = Lost / Generated × 100**, success = Received / Generated × 100입니다. Outage-only 구간의 failure는 100%입니다. link loss / attempted는 별도 attemptedLinkLossRatio로 보존하고 attempted=0이면 NaN입니다.

Rolling은 (t−5초,t]에 생성된 패킷을 분모로 합니다. 첫 5초는 실제 관측된 부분 창을 사용합니다. Throughput은 창 내 received 수를 실제 창 길이로 나눈 packets/s이며 시작 패킷의 시간 구간까지 포함합니다. 손실에 영향을 주는 미정 결과가 있는 창은 N/A입니다.

고정 seed의 독립 RandStream을 사용해 재현 가능하며 MATLAB 전역 RNG를 바꾸지 않습니다. 패킷 크기는 간소화한 UDP datagram이며 IP/L2 overhead는 제외합니다. 카운터는 생성/송신 시각에 귀속한 최종 결과이며 지연 후 도착 시각의 소켓 수신 이벤트 곡선은 아닙니다.

## 결과 화면 — viewer + 일반 Figure 2개

1. **3D GSL**: GS, 후보, 단일 serving, handover 색 전환.
2. **Serving / Handover Summary**: serving ID 범주 축 + 후보 수(0이면 outage), handover 세로 점선, 3D 재생/정지 버튼.
3. **Packet Transmission Performance**, 3개 패널:
   - generated / attempted / received / total lost 누적.
   - rolling Lost/Generated failure ratio (%).
   - rolling received throughput (packets/s).
   - 각 패널의 handover 선은 상관관계 확인용이며 손실을 강제로 발생시키지 않습니다.

위성별 elevation/SNR/delay/Doppler 그래프는 기본 출력에서 제외합니다. Elevation/range/FSPL/SNR/속도/radial velocity/raw Doppler/전송 지연은 CSV/MAT에 보존합니다. ID는 크기 비교 대상이 아니므로 동일 간격 범주 축을 쓰며 실제 no-serving은 0 (none)입니다.

## 결과 파일

기본 results_packets 폴더의 같은 파일을 갱신합니다.

| 파일 | 내용 |
|---|---|
| geometry_stage1.mat | CFG/G, 모든 위성 elevation/range/visibility, 시작/끝 ECEF 위치 |
| visibility_summary.csv | 후보 수/유무, 최대 elevation, 고정 예시 위성 ID/elevation |
| satellite_index.csv | MATLAB 배열 인덱스/이름, NORAD ID 아님 |
| link_state.csv | serving/handover, 물리 상태, 후보, ECEF 속도 |
| packet_results.csv | generated/attempted/transmitted/received/lost/outage_loss/link_loss/pending, PER, rolling, 누적 카운터 |
| packet_results.mat | P/M/L/CFG |
| packet_summary.txt | 최종 집계, handover/outage 기간/성공률/평균 throughput |
| serving_handover.png | Figure B |
| packet_performance.png | Figure C |
| serving_debug.csv | CFG.debug=true일 때 선택 이력 |

과거 link_performance/cumulative_packets/rolling_packet_loss/visibility/environment_3d PNG는 해당 결과 폴더에서 정리합니다. results_packets_stress는 과거 호환 폴더이며 이제 기본값도 60pps입니다. 새 기본 결과는 results_packets를 사용하세요.

## 검증과 요구사항

실행 환경: **MATLAB R2026a Update 5 + Aerospace Toolbox**. Simulink/Communications Toolbox/Satellite Communications Toolbox 함수를 추가로 사용하지 않습니다.

```matlab
verify_packets
verify_packet_integration
verify_visualization
```

현재 검증 로그: validation_packets_current.log, validation_current_gsl.log. 이전 validation_*.log는 과거 모델/버전 검증 이력입니다.

경계 시험은 4° 정확한 차이, 후보 상실, outage/reacquisition, all-success/all-loss, 생성 분모의 moving-window oracle, 미정 PER, RNG 재현성과 invalid PER를 확인합니다. 3D 시험은 실제 1,584기 시나리오와 모든 handover 시각의 단일 빨간 링크, 이전 색 복귀를 확인하며, 별도 실제 90° mask 소형 시나리오로 serving=none/100% outage를 검증합니다. 테스트용 임의 확률은 연구 결과에 내보내지 않습니다.

## 향후 연구

실제 PHY/패킷 길이에 맞는 검증 SNR→PER, fading/강우/간섭, 실제 handover 중단 측정, Python ISL 연동, E2E delay/jitter/deadline miss, RL routing.

## 이번 변경 파일

- configGSL.m: 160 Bytes / 60pps 및 명시적 BPSK 참조 대역폭.
- selectServingSatellite.m: >= margin, 후보 상실 즉시 전환/outage.
- GSLViewerController.m: 단일 red target/이전 색 복귀, 시각·후보·handover·outage 제목.
- main_gsl_simulation.m, playGSL.m, 신규 attachGSLPlaybackControls.m: 동기식 3D 재생/정지 버튼.
- getPERfromSNR.m: 명시적 uncoded BPSK/AWGN 참조 BER→PER.
- simulatePacketTransmission.m, computePacketMetrics.m: attempted, outage/link/total loss, generated 분모 rolling, throughput.
- plotResults.m, reportPacketResults.m: 핵심 Figure 2개, CSV/MAT/최종 요약.
- README.md, PACKET_LAYER.md 및 저장소 root README: 모델·정의·실행·제한.
- verify_packets.m, verify_packet_integration.m, verify_visualization.m: 현재 모델의 경계·집계·실제 viewer 검증.
- 신규 validation_packets_current.log, validation_current_gsl.log: 현재 실행 증거.
