# 26-2capstone2

명지대학교 26-2 캡스톤디자인2

## GSL uplink (2026-10-29)

이 GSL 브랜치의 최신 실행 경로: **gsl → main_gsl_simulation.m**

[실행 안내](gsl/README.md) · [측정 공식·채널 가정·결과 파일](gsl/GSL_UPLINK_GUIDE.md)

평가 범위는 지상국에서 ISL에 진입하는 첫 번째 위성까지입니다. 600초·1,584개 위성과 기본 3D 재생 기능을 유지하고, 원본 패킷 번호별 성공·손실·기한 초과·처리 중 상태를 별도 창으로 표시합니다. 박스를 누르면 대상 위성, 손실 위치와 원인, 시각을 확인할 수 있습니다.

```matlab
R = main_gsl_simulation;
```

기본 실행은 **인공 감쇠를 넣은 기능 검증 시험**입니다. 측정된 Starlink 환경이나 일반적인 실제 손실률을 주장하지 않습니다. GSL 20ms 기한과 RF/채널 값은 연구 가정이며 configGSL에서 변경할 수 있습니다. ISL 코드·ML·전력 제어·복제 전송은 이번 변경 범위에 포함하지 않습니다.

검증 명령: `verify_uplink`. 재생·패킷 선택 검증 및 결과는 gsl/validation_uplink.md를 참고하세요.
