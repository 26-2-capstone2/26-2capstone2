# 26-2capstone2 — GSL

최신 코드는 gsl 폴더입니다. Ku uplink **14 GHz / 50 MHz / 정보율 50 Mbps**, 지상국→첫 위성까지 평가합니다.

## 맑음 / 흐림 / 비 세 조건 실행

MATLAB Current Folder를 gsl로 맞추고:

```matlab
B = main_gsl_weather_comparison;
```

동일한 600초 위성 기하·트래픽으로 ITU 기체·구름·강우 흡수를 비교합니다. 결과는 results_weather/clear, cloudy, rainy 및 weather_comparison.csv/.png에 저장합니다. 특정 날짜의 실제 기상 관측을 불러온 결과는 아니며 입력값과 한계는 문서에 명시했습니다. 기존 인공 10dB 감쇠는 날씨 실험에서 사용하지 않습니다.

[날씨 입력·모델·실행 안내](gsl/WEATHER_MODEL.md) · [기본 패킷/3D 안내](gsl/README.md)

![날씨별 비교](gsl/docs/weather_comparison.png)

기존 3D 기본 재생바와 번호별 패킷 창은 한 조건을 선택해 사용합니다:

```matlab
R = main_gsl_simulation(configGSL('rainy'));
```

검증: verify_uplink, verify_weather. 전력 제어·ML·복제 전송·혼잡 큐는 아직 포함하지 않습니다.
