# 26-2capstone2 — GSL

## 최신 MATLAB 코드 — 2026-11-23

GSL 브랜치의 `gsl` 폴더를 MATLAB 현재 폴더로 설정하고 실행한다.

```matlab
R = main_gsl_ddqn_6x11;
```

6×11 위성군·환경감쇠 6 dB에서 최근 최대 5초 SNR 변화 추세를 입력으로 사용하는 후보별 Double DQN이다. 100개 에피소드 학습 후 학습에 쓰지 않은 시드 10개로 평가하며, 후보 SNR 표와 1~10회 패킷 재생 창을 제공한다. 범위는 지상국→선택된 첫 수신 위성까지만이다.

GitHub에는 코드와 실행에 필요한 PHY 표만 포함한다. 저장 결과가 없는 첫 실행은 학습·평가를 수행하므로 시간이 걸린다. 이후에는 해당 PC에 저장된 결과를 연다. 기존 방식·최대 SNR과 동일 시드 비교는 아직 하지 않았으므로 개선율은 확정하지 않는다.

[6×11 DDQN 실행·설정·검증](gsl/ddqn_6x11/README.md)

## 이전 실행 파일

- `main_gsl_three_constellations`: 6×11 / 20×20 / 36×36, 세 정책 비교. [설명](gsl/three_constellations/README_GSL_THREE.md)
- `main_gsl_toolbox_simulation`: 단일 위성군, 툴박스 PHY, 환경감쇠 슬라이더. [PHY 설명](gsl/README_TOOLBOX_PHY.md)
- `main_gsl_simulation`: 기존 JPL PHY 비교.
