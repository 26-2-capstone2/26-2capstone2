# GSL Double DQN 사용법

MATLAB 현재 폴더를 이 문서가 있는 gsl 폴더로 설정한다.

## 실행

train_gsl_ddqn.m을 열고 F5로 실행한다. Deep Learning Toolbox가 필요하다. 기본 20회 학습이며 1회마다 600초를 계산한다. 실행 시간은 PC에 따라 달라진다.

~~~matlab
R = train_gsl_ddqn();
~~~

짧게 연결을 확인하려면 다음처럼 실행한다. 이 실행은 학습 안정성이나 성능 개선을 결론 내리기 위한 횟수로 정한 값이 아니다.

~~~matlab
O = configGSLDQN();
O.numEpisodes = 2;
O.evaluationSeeds = 20263001;
R = train_gsl_ddqn(O);
~~~

기본 검증은 verify_gsl_ddqn을 실행한다. 실제 궤도 없이 Double DQN의 목표 점수 계산, 빈 후보 제외, 종료 처리, 경험 저장, 신경망 갱신, 목표 신경망 갱신을 확인한다.

## 학습 구조

- 환경감쇠 8 dB, 600초, 1초마다 결정.
- 입력은 현재 시나리오 기준 79개. 은닉층은 ReLU를 적용한 64개, 64개. 출력은 후보 순위별 Q값 13개.
- 온라인 신경망이 다음 상태에서 가장 좋은 유효 행동을 고른다. 목표 신경망이 그 행동의 점수를 평가한다.
- 목표값은 reward + gamma * targetQ(nextState, bestOnlineAction)이다. 에피소드 종료 시에는 reward만 사용한다.
- 현재 선택, 무작위 탐색, 다음 상태의 최선 행동 계산 모두 빈 후보를 제외한다.
- 후보가 하나도 없으면 MATLAB에는 action=0을 전달하며, 학습 배열의 1번 칸은 그 상황의 강제 연결 불가 행동을 나타낸다. 종료 직전이 아닌 연결 불가 상태에도 이후의 보상이 연결된다.
- 원본 패킷별 난수와 에이전트의 탐색·학습 난수는 별도로 관리한다.
- 보상은 기존 기한 내 도착, 연속 손실, 핸드오버 가중치 1 / 0.5 / 0.05를 사용한다.

경험 저장 공간에서 무작위로 64개씩 추출한다. 512개 경험을 모은 뒤 환경 4초마다 학습하며, Adam 학습률 0.001과 Huber 오차를 사용한다. 할인율은 0.99, 목표 신경망은 학습 갱신 100회마다 복사한다. 기울기 크기는 5로 제한한다.

탐색 확률은 환경 10,000 step 동안 1에서 0.05까지 감소한다. 기본 20회는 학습을 시작하기 위한 예산이며, 보상이 안정되는지와 실제 패킷 성능을 확인해 횟수와 설정을 조정해야 한다. 탐색 중인 학습 결과와 탐색을 끈 평가 결과를 구별한다.

configGSLDQN.m에서 학습 설정과 시드를 수정할 수 있다. 학습 시드 개수는 numEpisodes 이상이어야 하며 평가 시드와 겹치면 오류로 중단한다. 20회 이상이면 trainingSeeds의 범위도 함께 늘린다.

## 저장되는 결과

매 에피소드마다 results_ddqn/실행시각 폴더에 training_history.csv와 agent.mat을 저장한다. agent.mat에는 마지막 완료 에피소드의 모델, 목표 신경망, 학습 설정, 경험 저장 공간 및 학습 이력이 포함된다.

학습이 끝나면 고정된 마지막 모델을 사용해 별도 평가 시드마다 다음 세 방식을 비교한다.

1. 기존 고도각 최대 + 4도 유지 조건.
2. 매초 최고 SNR 후보 선택.
3. 학습한 Double DQN의 Q값이 가장 높은 유효 후보 선택. 탐색 확률은 0.

세 방식은 같은 평가 시드에서 같은 원본 패킷 난수를 사용한다. evaluation_summary.csv에는 손실률, 기한 내 도착률, 최대·평균 연속 손실, 핸드오버 횟수, 원인별 손실 및 검증식 손실률을 기록한다.

첫 번째 평가 시드의 전체 패킷 기록과 연속 손실 구간을 방식별 CSV로 저장한다. training.png와 comparison.png로 학습 경과와 평가 평균을 볼 수 있다. makePlots=false면 그래프 생성을 끌 수 있다.

저장된 모델로 평가를 다시 실행할 수 있다.

~~~matlab
S = load('저장된 결과 폴더/agent.mat');
comparison = evaluate_gsl_ddqn(S.agent, S.O);
~~~

## 결과 해석

학습으로 개선됐다고 가정하지 않고 기존 방식과 최고 SNR 방식의 결과를 함께 확인한다. 학습과 평가에서 궤도는 동일하며 패킷 난수 시드를 분리했다. 다른 궤도나 시작 시각에 대한 일반화는 별도 실험이 필요하다.

모델과 설정을 고를 때 사용한 평가 시드는 검증용으로 간주하고, 최종 성능 보고는 추가로 확보한 시드에서 진행한다. 손실률과 연속 손실뿐 아니라 기한 내 도착률도 함께 확인한다.

참고 문서

- [MathWorks custom training loops](https://www.mathworks.com/help/deeplearning/ug/custom-training-loops.html)
- [MathWorks DQN 설명](https://www.mathworks.com/help/reinforcement-learning/ug/dqn-agents.html)
