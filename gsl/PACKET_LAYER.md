# GSL 패킷 계층과 추가 link-state 모델

이 버전은 **MATLAB 내부의 패킷 단위 시뮬레이션**입니다. 네트워크 소켓으로 UDP를 송수신하거나 실제 장비의 수신 결과를 측정하지 않습니다. 기존 1단계의 constellation/GS/elevation/access/3D 코드는 유지하고, 후속 계층을 추가했습니다.

## 현재 구현 범위

| 계층 | 구현 상태 |
|---|---|
| 기존 geometry / 3D viewer | 기존 코드 유지 |
| Serving / handover | 최고 elevation + 4° hysteresis |
| Propagation delay | 실제 slant range / 빛의 속도 |
| SNR | 아래의 명시적 대역폭 가정을 둔 Ku-band downlink 참조 모델 |
| Doppler | ECEF 상대속도의 LOS 성분, 이상적 보상 후 residual=0 |
| 패킷 발생 / 송신 시도 | 구현 및 카운터 분리 |
| PER / 수신·손실 결과 | **근거 있는 곡선이 없어 미정** |
| 누적 / rolling 그래프와 CSV/MAT | 구현; 미정 값을 0으로 그리지 않음 |

업스트림은 GSL 브랜치 `279d9de1b7dbbd6c3286103f712c63a46c579cae`입니다. 해당 버전에는 geometry만 있었으므로 사용자 확인 후 serving/link-state도 추가했습니다. RF 수치는 사용자 제공 참조값이며 특정 운용 Starlink 시스템의 성능을 검증했다는 의미는 아닙니다.

## 실행

MATLAB에서 이 파일과 `.m` 파일들이 있는 폴더를 Current Folder로 설정합니다.

```matlab
R = main_gsl_simulation;
play(R.scenario);
R.packetTable(1:10,:)
R.packetMetrics
```

기존 geometry만 실행하려면 `CFG.enablePackets=false`를 사용합니다.

```matlab
CFG = configGSL();
CFG.openViewer = false;
CFG.packetRate_pps = CFG.stressPacketRate_pps; % 60 pps: stress/sensitivity
CFG.outputDir = fullfile(pwd,'results_stress');
R = main_gsl_simulation(CFG);
```

baseline은 150 Bytes/20 pps이며 stress는 60 pps입니다. packet time은 `[0,T)`이므로 600초에서 각각 정확히 **12,000 / 36,000개**입니다. 채널 시간축은 기존처럼 `[0,T]`, 1초 간격입니다. 두 시간축을 같게 만들지 않았습니다.

## 코드 연결

`main_gsl_simulation` → 기존 `computeGeometry` → `computeLinkState` → `simulatePacketTransmission` → `computePacketMetrics` → `reportPacketResults`.

| 파일 | 변경 / 역할 |
|---|---|
| `configGSL.m` | 트래픽·hysteresis·RF·PER 함수 핸들·난수 seed 설정 추가 |
| `main_gsl_simulation.m` | 기존 geometry 처리 뒤 패킷 계층 호출; R에 linkState/packetTable/packetMetrics 추가 |
| `selectServingSatellite.m` | 결정론적 serving 선택과 handover 이벤트 |
| `computeLinkState.m` | serving별 거리·지연·SNR·Doppler를 1초 table로 정리 |
| `getPERfromSNR.m` | 근거 곡선을 넣을 위치; 현재 전부 NaN 반환 |
| `simulatePacketTransmission.m` | 패킷 발생 시각에 직전 채널 상태를 적용하고 PER 기반 결과 결정 |
| `computePacketMetrics.m` | 누적 카운터, 총 비율, 실제 이동 시간 윈도 집계 |
| `reportPacketResults.m` | Command Window 요약, 그래프, CSV/MAT/텍스트 저장 |
| `verify_packets.m` | 독립적인 집계·시간축·경계조건 소프트웨어 테스트 |
| `verify_packet_integration.m` | 1,584기 실제 시나리오를 실행하는 통합 검증 |

`createConstellation.m`, `computeGeometry.m`, `plotResults.m`의 geometry 계산은 변경하지 않았습니다. `verify_stage1.m`은 기존 검증에서 새 계층을 끄는 한 줄만 추가했습니다.

## 카운터와 미정 값

- **Generated**: 생성한 전체 패킷.
- **Transmitted**: 해당 시각에 serving index > 0이고 `isLinkAvailable=true`인 패킷. 현재 availability는 serving+visibility로 정의하며 임의 SNR 임계값을 적용하지 않습니다.
- **Received / Lost**: 송신한 패킷 중 PER로 판정된 성공 / 손실. PER 미정인 송신 패킷은 두 값 모두 NaN입니다.
- **Not transmitted**: 생성했지만 송신하지 못한 패킷. PER 손실에 포함하지 않습니다.
- **Outcome pending**: 송신했지만 PER가 없어 결과를 정하지 못한 패킷. 비행 중이라는 뜻이 아니라 **모델 미정**이라는 뜻입니다.

미송신 패킷의 received/lost는 0, per는 NaN입니다. 미정 송신 패킷이 하나라도 있으면 전체 received/lost와 비율도 N/A로 표시합니다. 이미 판정된 부분만 보고 싶으면 `resolvedReceivedPackets`와 `resolvedLostPackets`를 확인할 수 있습니다.

PER가 모두 알려졌을 때 `Received + Lost = Transmitted <= Generated`가 성립합니다. 현재 placeholder에서는 `ResolvedReceived + ResolvedLost + Pending = Transmitted`로 검증합니다. 미정 값 때문에 위 첫 식을 거짓으로 충족시키지 않습니다.

PLR = 100×Lost/Transmitted, PDR = 100×Received/Transmitted입니다. Transmitted=0이면 두 값 모두 NaN(정의 불가)입니다. 참고값 Generated-to-Received는 100×Received/Generated입니다.

## 시간과 모델 가정

패킷은 주기적으로 생성되며 `[channelTime(k),channelTime(k+1))`에는 k번째 채널 상태를 유지합니다. 채널 경계의 패킷은 새 상태를 사용합니다. 큐·재전송·혼잡·별도 handover 중단 시간은 모델링하지 않습니다. 송신하지 못한 패킷을 다음 시간으로 보류하지 않습니다. 직렬화 시간은 150×8/50e6=24μs=0.024ms이며, 데이터율이 너무 낮아 패킷 간격보다 길어지면 큐 모델이 필요하다는 오류를 냅니다.

수신/손실 카운터는 **송신 시각에 귀속된 최종 결과**입니다. 전파 지연 후 실제 도착한 시각을 나타내는 수신 이벤트 누적 곡선은 아닙니다. 저장한 propagation/transmission delay를 향후 E2E arrival-time 모델에 사용할 수 있습니다.

Rolling PLR은 각 패킷 시각 t에서 **(t−5초,t]**의 송신 패킷만 분모에 사용합니다. 초기 5초는 가능한 표본만 사용합니다. 창 안에 송신이 없거나 미정 송신 결과가 있으면 NaN입니다. 미정 결과가 창 밖으로 빠지면 이후 완전한 창은 계산될 수 있습니다. 패킷 간격의 반올림 오차를 제외하고 시간으로 창을 이동하며, 누적 평균을 복사하지 않습니다. baseline의 충분히 채워진 창은 100개, stress는 300개입니다.

Handover는 기존 satellite>0에서 다른 satellite>0으로 바뀔 때만 집계합니다. 최초 연결, outage 진입, 재연결은 handover에 포함하지 않습니다. 새 후보 elevation이 현재보다 **엄격히 4° 초과**할 때 전환하며, 기존 serving이 안 보이면 가시 후보로 바로 전환합니다. 동률 후보는 가장 작은 위성 인덱스를 선택합니다. 패킷 table의 `handover_event`는 이벤트 직후 첫 패킷에 한 번, `handover_state`는 해당 채널 구간의 모든 패킷에 표시합니다. 그래프 점선은 원래 link-state 이벤트 시각을 사용합니다.

## SNR 및 Doppler 단위

Ku-band **DOWNLINK**: fc=12GHz, EIRP density=12.88 dBW/MHz, G/T=13.7 dB/K. 전체 신호 전력과 잡음 전력의 비율인 SNR=C/N입니다. Eb/N0나 Es/N0가 아닙니다.

```
EIRP_density_dBW_per_Hz = EIRP_density_dBW_per_MHz - 60
FSPL_dB = 20 log10(4*pi*range_m*fc_Hz/c_mps)
SNR_dB = EIRP_density_dBW_per_Hz + G/T - FSPL_dB
         - 10 log10(k) + 10 log10(Bsignal/Bnoise)
```

c=299792458 m/s, k=1.380649e−23 W/(K·Hz). 평탄한 송신 PSD와 신호 대역폭=수신 잡음 대역폭을 가정하여 기본 비율은 1입니다. **절대 RF 대역폭을 50Mbps 데이터율과 동일시하지 않았습니다.** 전체 EIRP 또는 Eb/N0가 필요하면 절대 대역폭과 PHY 정의를 추가해야 합니다. 기타 손실과 간섭은 이번 참조 모델에서 제외합니다. 실제 링크 성능 보장을 뜻하지 않습니다.

ECEF에서 고정 GS 속도는 0이며 `states(...,'CoordinateFrame','ecef')`의 위성 속도를 사용합니다. LOS 단위벡터와 속도의 내적을 radial velocity로 두고 `rawDoppler=−(radialVelocity/c)*fc`를 계산합니다. 접근 양수/이탈 음수이며 ideal compensation으로 residual=0입니다. Doppler나 handover를 SNR/PER에 임의 penalty로 반영하지 않습니다.

공식 근거: [MathWorks Link Budget](https://www.mathworks.com/help/satcom/gs/satellite-link-budget.html), [states ECEF 속도 정의](https://www.mathworks.com/help/satcom/ref/matlabshared.satellitescenario.satellite.states.html). 코드의 PSD 식은 공식 C/N0 식에서 동일 신호/잡음 대역폭을 적용한 유도식입니다.

## PER 연결

`CFG.perModel`은 SNR 벡터를 받아 같은 개수의 PER(0~1 또는 미정 NaN)을 반환하는 함수 핸들입니다. 기본 `getPERfromSNR`는 모두 NaN입니다. 유한한 PER를 반환하려면 `CFG.perModelSource`에 출처와 적용 조건을 명시해야 합니다. 단순히 문자열을 넣는 것은 과학적 타당성 검증을 대신하지 않습니다.

곡선을 준비할 때 QPSK+AR4JA rate 1/2, coding/frame length, 패킷→코드블록 매핑, SNR/EbN0 정의, 적용 범위와 보간 정책을 확인해야 합니다. 범위를 벗어난 값은 근거 없이 외삽하지 말고 NaN을 반환할 수 있습니다. 사용자 제공 PER가 없으므로 이번 결과에는 손실 확률이나 0% 손실선을 만들지 않았습니다.

모델이 연결되면 독립 Bernoulli 추첨 `rand < per`로 판단하며 전용 RandStream과 seed로 재현됩니다. MATLAB 전역 RNG 상태는 변경하지 않습니다. 이는 독립 패킷 오류 가정이며 burst 모델은 포함하지 않습니다.

## 그래프와 데이터

기존 geometry figure/3D snapshot을 유지하고 다음을 추가합니다.

1. Serving / propagation delay / SNR: 세 패널. Serving과 SNR에 handover 점선.
2. **Cumulative UDP Packet Transmission**: 네 누적 선. 겹치는 generated/transmitted는 실선/점선으로 구분하고 미정 received/lost는 범례에 N/A로 표시.
3. **Rolling Packet Loss Ratio**: 5초 PLR과 handover 점선. PER 미정 시 설명만 표시하고 가짜 선은 그리지 않음.

기본 출력 폴더는 `results_packets`입니다. `geometry_stage1.mat`와 기존 geometry CSV는 이전 형식 그대로 저장하며, 다음 파일을 추가합니다.

- `link_state.csv`: 1초 link-state, serving/handover/지연/FSPL/SNR/raw·residual Doppler.
- `packet_results.csv`: 패킷당 ID, time_s, serving_sat_id, generated/transmitted/received/lost, snr_dB, per, propagation_delay_ms, handover_event/state, transmission_delay_ms, outcome_pending/not_transmitted, rolling_loss_ratio_pct, 누적 4개 카운터.
- `packet_results.mat`: 확장 table P, metrics M, link-state L, CFG. time_s는 숫자 초이며 MAT의 table/함수 핸들은 Python에서 직접 읽기 번거로우므로 **Python 연동은 CSV 권장**.
- `packet_summary.txt`, `link_state.png`, `cumulative_packets.png`, `rolling_packet_loss.png`.

CSV의 미정 수치(NaN)는 MATLAB 출력에서 빈 칸으로 저장될 수 있습니다. Python/pandas의 기본 NA 파싱을 유지하고, 빈 칸을 0으로 채우지 마세요. 시각은 기존 `CFG.startTime` UTC로부터의 초입니다. 패킷 ID와 위성 인덱스는 MATLAB의 1-based 정수입니다.

## 검증

```matlab
verify_packets             % 빠른 소프트웨어 경계조건 검증
verify_packet_integration  % 기본 600초 실제 geometry 포함, 결과 파일 저장
```

단위 검증의 PER=0/1 및 RNG 확률은 **소프트웨어 테스트용 가상 입력**이며 연구 모델/출력에 쓰지 않습니다. 20/60 pps, 0송신, outage, 미정 PER, 성공/손실 회계, 정확한 sliding window, hysteresis 및 전역 RNG 보존을 검증합니다. 통합 검증은 ECEF range-rate를 거리 중앙차분과 비교하고 PSD 기반 SNR을 동일 대역폭의 전체 EIRP 식과 비교합니다. CSV/MAT 읽기 복원도 확인합니다.

### 실제 검증 결과 — 2026-10-03

MATLAB R2026a Update 5 + Aerospace Toolbox에서 통과했습니다. 테스트 보조 코드에도 추가 Toolbox가 필요하지 않게 구성했습니다.

| 항목 | Baseline | Stress (동일 실제 geometry 재사용) |
|---|---:|---:|
| 시뮬레이션 길이 | 600초 | 600초 |
| 발생률 | 20 pps | 60 pps |
| Generated | 12,000 | 36,000 |
| Transmitted | 12,000 | 36,000 |
| Received / Lost | N/A / N/A | N/A / N/A |
| Pending | 12,000 | 36,000 |
| 5초 창의 송신 수 (충분히 채워진 경우) | 100 | 300 |
| Handovers | 10 | 10 |

기본 GS와 10분 구간에서 serving이 계속 유효했습니다. 지연 범위 1.863~2.447ms, 참조 SNR 23.840~26.206dB입니다. 통합 실행 약 75.8초(환경에 따라 달라짐). 상태가 나빠지면 손실이 증가한다는 결론은 PER가 없으므로 아직 낼 수 없습니다. 출력 그래프는 실제로 열어 표시 내용을 확인했습니다.

`validation_packets.log`와 `validation_packets_stress.log`에 검증 로그를 남겼습니다. 후보 부재/명시적 outage, 모두 성공/모두 손실, 혼합 미정 구간 후 rolling 계산 회복은 별도의 소프트웨어 테스트에서 통과했습니다.
