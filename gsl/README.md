# GSL 시뮬레이터 — 최신 패킷 계층 버전

현재 실행 대상은 이 폴더의 `main_gsl_simulation.m`입니다. 2026-10-03 검증한 geometry + serving/handover + link-state + packet 계층을 포함합니다. 이전 코드는 Git 이력에서 확인할 수 있습니다.

## 실행

MATLAB의 Current Folder를 이 README와 .m 파일들이 있는 폴더로 설정합니다.

```matlab
R = main_gsl_simulation;
play(R.scenario);
```

필요 환경: MATLAB + Aerospace Toolbox. 실제 검증 환경은 R2026a Update 5입니다.

## 팀원용 문서

- [상세 설명·설정·모델 가정·CSV/MAT 형식](PACKET_LAYER.md)
- [600초 통합 검증 로그](validation_packets.log)
- [60 pps 및 경계조건 검증 로그](validation_packets_stress.log)

## 구현 상태

- 550 km / 53° / 72면 × 22기 = 1,584기, GS 및 elevation ≥25° 가시성, 3D viewer
- 최고 elevation + 4° hysteresis serving/handover
- Propagation delay, Ku-band DOWNLINK 참조 SNR, 보상 전 Doppler
- UDP 패킷 생성, 송신 시도, 누적 카운터와 5초 rolling loss 구조
- CSV/MAT, 그래프, Command Window 요약

**PER 곡선은 아직 없습니다.** 따라서 수신·손실 및 손실률은 N/A이며 0% 손실을 뜻하지 않습니다. 이는 실제 UDP 소켓 송수신이 아닌 패킷 단위 시뮬레이션입니다.

600초 검증: 20 pps는 생성/송신 12,000개, 60 pps는 36,000개. 기본 시나리오 handover 10회. 기존 geometry, 집계 및 CSV/MAT 복원 검증 통과.

## 설정과 결과

`configGSL.m`에서 GS 위치, 시간, 트래픽 등을 변경합니다. GS 기본값은 임시 예시 좌표입니다. 기본 출력은 `results_packets/`입니다. Stress는 `CFG.packetRate_pps=CFG.stressPacketRate_pps`로 설정하고 별도 outputDir를 지정하세요.

```matlab
verify_packets
verify_packet_integration
```

기존 geometry만 실행하려면 `CFG.enablePackets=false`를 사용합니다. `validation_stage1.log`는 초기 geometry 검증 기록입니다.
