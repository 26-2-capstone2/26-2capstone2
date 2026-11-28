# 저장된 학습 중간 모델 비교

`점검결과.txt`에 전체 결과와 구체 사례를 정리했다.
기존 1,000회 학습에서 보존된 100·200·…·1,000회 모델을 탐험 없이 같은 시드 10개에서 평가했다.
새 학습이나 기존 체크포인트 변경은 없으며, 100회 모델은 앞선 n-step 실험의 1-step 원본 평가와 일치한다.

## 실행

- 상위 `gsl`에서 `main_gsl_checkpoint_comparison`: 저장 그림 열기, 새 학습·평가 없음.
- `run_entry.m`: 10개 모델 × 10개 시드 재평가. 원래 저장된 checkpoint와 nstep_1127의 100회 기준 결과가 필요하다.
- `probe_regression_case`: 200회 모델의 시드 20279302에서 1초의 선택만 바꾸는 사후 실험.

## 자료

- `results/runs.csv`: 전체 100회 평가.
- `results/summary.csv`, `paired_differences.csv`: 중간 모델별 평균·표준편차 및 100회 대비 쌍체 차이.
- `results/reference_state_scores.csv`: 100회 모델의 동일한 6,000개 상태에서 모든 모델의 Q순위와 선택 비교.
- `results/worsened_burst_windows.csv`: 100회보다 최대 손실이 증가한 회차의 손실 전후 선택·PER·Q점수.
- `results/regression_case_200_repeat02.csv`: 선택 하나만 바꾼 구체 사례.
- `results/episode_XXXX_repeat_YY`: 모든 회차의 packets.csv·decisions.csv·loss_runs.csv·decision_quality.csv·preview.mat.
- `verification.json`: 3,600,000개 패킷 집계·연속 손실·보상 및 동일 난수 독립 검증.

## 해석 주의

같은 훈련 과정의 중간 모델이며 독립 학습 초기값 10개가 아니다.
동일 상태에서 다른 행동을 고른 것은 Q순위 변화에 대한 관측이다. Q와 단일 sampled return의 차이를 참 Q오차라고 부르지 않는다.
평가의 후속 정책에는 Q마진이 적용되며, 원래 Q 타깃은 greedy이므로 둘의 차이도 진단값에 섞일 수 있다.
중간 모델 선택에 이 시드를 이용하면 검증용 시드이며, 최종 모델 성능은 새 시드로 별도 확인해야 한다.
물리적 낙관적 하한과 정책 때문에 추가된 손실을 구분한다. 이 실험은 왜 학습 성능이 등락하는지 관찰한 것이며 최적화 원인의 분리 검증은 아니다.
