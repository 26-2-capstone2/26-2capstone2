# 정적 6×11 / 20×20 / 36×36 비교 — 2026-11-28

각 크기별 DDQN 수정 보상 100회 학습 및 세 정책의 동일 시드 10회 평가를 완료했다.

- `main_gsl_static_policy_comparison`: 6×11 저장 결과.
- `main_gsl_static_20x20`: 20×20 저장 결과.
- `main_gsl_static_36x36`: 36×36 저장 결과.
- `main_gsl_constellation_comparison`: 세 위성군 통합 비교 그래프.

위 명령은 저장 결과를 열며 재학습하지 않는다. 개별 명령에 `'run'`을 넘기면 해당 위성군을 새로 학습/평가한다. 최종 모델과 결과 MAT를 포함하고, 전체 패킷 로그는 바탕화면 `codex/1128`의 각 크기 폴더에 보관했다.

[통합 결과 표](위성군_비교/comparison_table.csv) · [실제 후보 수](위성군_비교/candidate_counts.csv) · [결과 해석](위성군_비교/결과해석.txt)

위성 간격을 유지하여 격자를 넓힌 비교다. 총 위성 수 증가가 GS의 가시 후보 수 증가를 보장하지 않는다. 각 크기에서 학습 초기화는 1개이며, 크기가 달라지면 채널 난수의 위성별 매핑과 후보 비율 입력도 달라진다. 과거 이동 환경 결과와 구분한다.

---

# 최신 정적 6×11 실험 — 2026-11-28

`main_gsl_static_policy_comparison`을 실행하면 이번 정적 환경의 저장 결과가 열린다. 최종 모델과 결과 MAT도 포함한다. 전체 반복 패킷 로그는 로컬 `codex/1128/6x11` 보관본에 있다.

- 6×11 정적 배치, GS 첫 열 근처, 고도각 25° 이상 후보, 매초 SNR 변화, 감쇠 6dB, Toolbox PHY.
- 최고 SNR·최고 고도각: 각각 학습 없이 10회 평가. DDQN: 수정 보상으로 100회 학습 후 같은 시드 10개로 평가.
- 손실률: 최고 SNR 6.7125%, 고도각 37.8075%, DDQN 5.3317%.
- 최대 연속 손실의 10회 평균: 45.4 / 793.6 / 45.5개. DDQN은 최고 SNR 대비 이 지표를 개선하지 못했다.
- 핸드오버: 최고 SNR 241.5회, 고도각 0회, DDQN 146회.
- 20×20, 36×36의 새 정적 실험은 아직 수행하지 않았다. 아래 과거 이동 환경 결과와 구분한다.

[이번 실험 실행 안내](static_reward_1128/POLICY_COMPARISON_README.txt) · [결과 해석](static_reward_1128/results_policy_comparison/20261128_010145_246/RESULTS_KO.txt) · [전체 30회 결과](static_reward_1128/results_policy_comparison/20261128_010145_246/runs.csv)

---

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

