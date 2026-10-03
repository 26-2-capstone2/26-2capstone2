# 26-2capstone2


명지대학교 26-2 캡스톤디자인2


## 노션 링크


https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## GSL — Continuous UDP Session / Handover

기존 `gsl/` MATLAB 프로젝트를 수정한 최신 실행 버전입니다.

- [실행 방법·세션 지표·연구 한계](gsl/README.md)
- [Packet layer 정의](gsl/PACKET_LAYER.md)
- [실제 JPL AR4JA curve 데이터 및 추출 근거](gsl/AR4JA_CURVE.md)
- [현재 MATLAB/3D 검증 로그](gsl/validation_udp_session.log)

```matlab
R = main_gsl_simulation;
playGSL(R);
```

GSL Session / Handover 창의 **Play / Resume 3D GSL** 버튼도 사용할 수 있습니다. Native viewer Play 대신 GSL 재생을 사용해야 serving 색상과 시간이 동기화됩니다.

600초 / 160 Bytes / 60 pps의 연속 UDP 세션, strict 4° hysteresis, 실제 handover event별 100 ms interruption을 사용합니다. Figure는 serving ID/elevation와 전체 세션 cumulative/rolling loss/received pps입니다.

PHY는 QPSK + CCSDS AR4JA rate 1/2, k=1024의 JPL Figure 14 CWER lookup으로 교체했습니다. Noise bandwidth와 information-rate 해석은 아직 근거가 부족해 TODO이며 미정 PHY는 성공/손실로 꾸미지 않습니다.

기본 실제 실행: Generated 36,000; actual handovers 10; confirmed handover loss 60; outage 0; unresolved PHY 35,940. 전체 Received/Lost/PLR은 N/A, 확정 손실 lower bound는 0.166667%입니다. OS UDP 실측이 아닌 packet-event simulation입니다.
