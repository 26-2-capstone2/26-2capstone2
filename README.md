# 26-2capstone2 — GSL

## 최신 MATLAB 코드 — 2026-11-22

GSL 브랜치의 `gsl` 폴더를 MATLAB 현재 폴더로 설정한다.

```matlab
R = main_gsl_three_constellations;
```

6×11 / 20×20 / 36×36 이동 위성군에서 최대 SNR, 최대 SNR+0.1 dB, 후보별 Double DQN을 비교한다. 학습 30개 에피소드와 평가 정책별 10회(총 90회), 후보 SNR 표, 패킷 재생 창을 구현했다. 범위는 지상국→선택된 첫 수신 위성까지다.

이번 업로드는 코드와 실행에 필요한 PHY 측정 표다. 대용량 실험 기록은 포함하지 않는다. 저장 결과가 없는 첫 실행은 학습·평가를 수행하므로 시간이 걸린다. 이후 실행은 해당 PC에 저장한 결과를 연다. 초기 DDQN의 기준 정책 대비 성능 개선은 아직 확인되지 않았다.

- [세 위성군 실행·설정](gsl/three_constellations/README_GSL_THREE.md)
- [툴박스 PHY 설명](gsl/README_TOOLBOX_PHY.md)

기존 단일 위성군 환경감쇠 슬라이더는 `main_gsl_toolbox_simulation`, 기존 JPL 방식은 `main_gsl_simulation`으로 실행한다.
