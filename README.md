# 26-2capstone2 — GSL

최신 실행 경로: **gsl → main_gsl_simulation.m → 실행(F5)**.

명령어·기상 설정을 바꾸지 않아도 맑음/흐림/비를 자동으로 계산하고, 기존 UDP SESSION PERFORMANCE 창 위쪽에 세 조건의 결과값을 함께 표시합니다. 오른쪽 날씨 선택으로 같은 그래프·SNR/연속 손실·번호별 패킷 화면을 바꿀 수 있습니다. 기존 3D 위성망과 재생 시간은 그대로 유지합니다.

RF: Ku uplink 14GHz / 잡음 대역폭 50MHz / 정보율 50Mbps. 기한은 GSL 전용 20ms 가정입니다. 결과는 results_weather/clear, cloudy, rainy에 저장합니다.

[실행 안내](gsl/README.md) · [날씨 입력·모델·한계](gsl/WEATHER_MODEL.md)

기상 관측을 불러온 실측은 아니며 명시한 기상 수치에 ITU 흡수식을 적용한 비교입니다. 인공 10dB 감쇠는 날씨 실행에서 사용하지 않습니다. 현재 세 조건의 SNR은 다르지만 신호 여유와 높은 SNR의 CWER 끝값 근사 때문에 손실·도착률은 동일합니다.

검증: verify_uplink, verify_weather, verify_weather_window. 기존 main의 600초·1,584개 위성 실행에서 세 날씨 자동 계산을 확인했습니다. ML·전력 제어·복제 전송·혼잡 큐는 아직 포함하지 않습니다.
