# 26-2capstone2


명지대학교 26-2 캡스톤디자인2


## 노션 링크


https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## GSL — Continuous Handover / Packet Performance

기존 `gsl/` 폴더의 최신 MATLAB 시뮬레이터입니다.

- [실행·모델·제한 설명](gsl/README.md)
- [패킷 집계 정의](gsl/PACKET_LAYER.md)
- [전체 MATLAB 검증 로그](gsl/validation_current_gsl.log)

```matlab
R = main_gsl_simulation;
```

Serving / Handover Summary Figure의 **Play / Resume 3D GSL** 버튼으로 색 동기화 재생합니다. 기본 viewer Play는 serving 색을 갱신하지 않습니다.

160 Bytes / 60 packets/s, inclusive 4° handover, 단일 serving과 outage 처리를 제공합니다. 일반 Figure는 serving/candidate 요약과 패킷 누적·rolling failure·received throughput 두 개입니다.

Lost는 outage loss + link loss이며 failure 분모는 generated입니다. 기본 PER는 명시한 ideal uncoded BPSK/AWGN 참조 모델로, 실제 Starlink PHY 검증 결과나 OS UDP 측정은 아닙니다.
