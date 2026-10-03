# Packet layer — 160 Bytes / 60 packets/s

현재 정의와 실행 안내는 [README](README.md)를 기준으로 합니다.

## 결과 정의 변경 (2026-10-03)

기존 lost는 시도 후 링크 손실만 포함했지만 **현재 lost는 outage_loss + link_loss**입니다.
기존 transmitted 열은 그대로 유지하되 attempted와 동일합니다.

- generated: 생성
- attempted/transmitted: serving 링크에서 즉시 시도
- received: 시도 후 성공
- outage_loss: 링크가 없어 미송신
- link_loss: 시도 후 PER 실패
- lost: 위 두 손실의 합
- outcome_pending: 시도했으나 PER가 NaN인 결과

분모는 전체 생성량입니다. packetLossRatio/rolling_loss_ratio_pct도 현재 **lost/generated**입니다.
조건부 링크 실패율은 attemptedLinkLossRatio=link_loss/attempted이며 attempted=0이면 NaN입니다.
CSV를 사용하는 Python 연동 코드도 이 의미 변경을 반영해야 합니다.

## 참조 PER

기본 getPERfromSNR은 uncoded coherent BPSK/AWGN BER에 독립 bit 오류를 가정하여 packet PER로 변환합니다.
160 Bytes, 50 MHz noise bandwidth, 50 Mbps gross bit rate가 명시된 참조 가정입니다.
실제 Starlink PHY 검증 모델이 아닙니다. 자세한 식·출처·제한은 README에 있습니다.
크기·대역폭·bit rate는 현재 CFG를 사용하며 CFG.perModel=[]가 이 기본 모델을 선택합니다.

검증 곡선을 확보하면 CFG.perModel 함수와 CFG.perModelSource를 설정합니다.
함수는 입력 SNR=C/N에 대해 같은 수의 [0,1] 또는 NaN 확률을 반환해야 합니다.
NaN 결과를 성공/실패 0으로 채우지 않습니다.

## 시간과 rolling

[0,T)에서 1/rate초마다 패킷 생성. Channel은 1초 간격 sample-and-hold.
각 패킷을 즉시 전송/실패 판정하고 큐/재시도는 없습니다.
Rolling은 (t−window,t]의 generated 분모를 사용하며 초기에는 실제 부분 창입니다.
미정 attempt가 창 밖으로 나가면 유효한 rolling 결과가 회복됩니다.

Throughput은 rolling received packets / observed window duration입니다.
평균 성공률은 total received / total generated이며 평균 throughput은 total received / simulation time입니다.
카운터는 생성/송신 시각에 귀속되며 실제 OS UDP 송수신이나 지연 후 도착 이벤트 곡선이 아닙니다.

## 출력

packet_results.csv/MAT에 outage/link/pending 및 누적·rolling 지표를 보존합니다.
link_state.csv에 SNR, delay, Doppler 등 보조 물리 정보를 보존합니다.
기본 그래프는 serving_handover.png와 packet_performance.png 두 개이며 native 3D viewer를 추가합니다.
재생은 Figure의 Play / Resume 3D GSL 버튼 또는 playGSL(R)를 사용합니다.
