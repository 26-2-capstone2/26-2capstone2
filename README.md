# 26-2capstone2


명지대학교 26-2 캡스톤디자인2


## 노션 링크


https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## GSL 시뮬레이터 — 최신 패킷 계층 버전

2026-10-03 검증한 최신 코드입니다. 기존 `gsl/` 경로에 갱신했습니다.

- [실행 안내](gsl/README.md)
- [패킷 계층·모델·결과 설명](gsl/PACKET_LAYER.md)
- [통합 검증 로그](gsl/validation_packets.log)

MATLAB에서 `gsl` 폴더를 Current Folder로 설정하세요.

```matlab
R = main_gsl_simulation;
play(R.scenario);
```

Geometry/3D, serving/handover, 지연/SNR/Doppler와 패킷 생성·송신·집계를 포함합니다. PER 근거 곡선은 아직 없으므로 수신·손실률은 N/A입니다. MATLAB 내부 시뮬레이션이며 실제 UDP 소켓 측정은 아닙니다.
