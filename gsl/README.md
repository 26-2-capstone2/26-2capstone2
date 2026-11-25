# GSL 최신 실행 코드

**2026-11-26 업데이트:** [최대 SNR 비교·1,000회 학습·Q점수 및 보상 점검·새 보상식 실험](UPDATE_20261126.md). 이전 100회 모델을 대체하는 최종 개선 모델은 아직 선정하지 않았다. 저장 결과 열기는 로컬 MAT 파일이 필요하며, GitHub에는 코드와 작은 요약 결과만 포함한다.

MATLAB에서 이 `gsl` 폴더를 현재 폴더로 선택한 뒤 실행한다.

- `main_gsl_three_constellations`: 6×11 / 20×20 / 36×36, 3정책 비교·후보 SNR 표·패킷 재생.
- `main_gsl_toolbox_simulation`: 기존 단일 위성군, 툴박스 PHY, 환경감쇠 슬라이더.
- `main_gsl_simulation`: 기존 JPL PHY 비교.

지상국에서 선택된 첫 수신 위성까지만 계산한다. ISL 내부 전달은 ISL 팀에서 담당한다.

GitHub에는 코드와 실행에 필요한 PHY 표를 올렸다. 대용량 결과 파일은 포함하지 않는다. 세 위성군의 첫 실행은 새 학습·90회 평가를 진행하므로 시간이 걸린다. 이후에는 해당 PC에 저장된 결과를 바로 연다.

[세 위성군 설정·모델·검증](three_constellations/README_GSL_THREE.md) · [툴박스 PHY](README_TOOLBOX_PHY.md) · [PHY 비교 기록](RESULTS_TOOLBOX_PHY_20261121.md)

이번 후보별 DDQN은 기존 팀원의 최종 모델과 다른 새 구조의 초기 모델이다. 성능 개선이 확인된 최종 정책으로 해석하지 않는다.

## DDQN 6×11 · 6 dB — 2026-11-23

main_gsl_ddqn_6x11 실행. 100회 학습 후 별도 시드 10회 평가를 완료한 결과와 회차별 후보 표·패킷 재생을 연다. 기존 방식 비교는 이번에 하지 않았다.

[실행·모델 설명](ddqn_6x11/README.md) · [10회 결과](ddqn_6x11/results_ddqn_6x11/20261123_160855_135/RESULTS.md)

