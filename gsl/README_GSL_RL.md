# GSL 강화학습 환경

MATLAB Current Folder를 이 문서가 있는 폴더로 설정한다. 기존 시각화 실행은 main_gsl_simulation, 강화학습 환경 생성은 GSLRLEnvironment를 사용한다.

- 환경감쇠 8.0 dB, 600초, 60 packets/s, 패킷 160 Bytes, GSL 기한 20 ms.
- 0초부터 599초까지 1초마다 위성 선택. 구간당 원본 패킷 60개.
- 후보는 앙각 조건을 충족하는 위성 전체. 감쇠 반영 SNR 내림차순이며, 동점이면 위성 ID 오름차순.
- 현재 위성이 계속 보이면 해당 순위를 선택해 연결을 유지할 수 있다. 위성 ID가 바뀌면 100 ms 핸드오버 중단이 적용된다. 첫 연결과 연결 불가 이후 재연결은 기존 모델의 핸드오버 정의를 따른다.

## MATLAB 연결 예시

~~~matlab
env = GSLRLEnvironment();  % 궤도와 후보별 SNR 준비. 에피소드 간 재사용.
candidates = env.reset(); % 기본 PHY 난수 시드. reset(seed)로 변경 가능.
disp(candidates)
state = env.observe(); % 고정 크기 입력과 선택 가능 마스크
done = false;

while ~done
    action = 0;
    if ~isempty(candidates)
        action = 1;  % 연결 예시. 매초 SNR이 가장 높은 후보 선택.
    end
    [candidates, feedback, done, packets] = env.step(action);
    reward = feedback.reward;
    nextState = env.observe();
end

[packetTable, metrics] = env.results();
disp(metrics.lossRuns)
~~~

## 팀원 코드와 주고받는 값

| 항목 | 내용 |
| --- | --- |
| candidates | time_s, rank, satelliteID, snr_dB, elevation_deg, isServing, snrChange_dB, hasSNRHistory |
| action | 현재 Table의 1부터 시작하는 순위. 후보가 없을 때만 0을 전달 |
| feedback | 해당 1초의 생성·수신·원인별 손실·기한 내 도착·지각 도착 개수, 핸드오버 여부, 끝에서 이어지는 손실 길이와 지금까지의 최대 연속 손실 |
| packets | 해당 구간의 원본 패킷 ID, 위성 ID, 손실 원인, 지연 및 도착 시각 등 |
| done | 600초 구간 처리가 끝나면 true. 이후 results()로 전체 결과 확인 |

후보 순위는 매초 달라질 수 있다. 순위의 숫자가 달라도 실제 위성 ID가 같으면 연결을 유지한다. Table에 포함된 시각은 현재 결정 시점이다. 후보 수는 매초 달라지며 env.maxCandidateCount로 기본 시나리오의 최대 후보 수를 확인할 수 있다. env.observe()가 고정 크기 입력과 빈 칸 마스크를 제공한다. 선택할 때와 Double DQN의 다음 상태 최대 Q값을 구할 때 모두 actionMask가 false인 칸을 제외한다. 후보가 전혀 없으면 환경에 action=0을 전달한다. 에피소드 종료 시에는 다음 상태 Q값을 사용하지 않는다.

verify_gsl_rl을 실행하면 기존 위성 선택 규칙을 강화학습 환경으로 재생해 36,000개 패킷 결과가 일치하는지 검사한다. 별도로 외부 위성 선택, 잘못된 순위 거부, 핸드오버 반영을 확인한다.

## State

후보별 SNR 변화량은 현재 값에서 같은 위성 ID의 직전 1초 값을 뺀 값이다. 처음 보이는 위성이나 0초에서는 snrChange_dB=0, hasSNRHistory=false로 표시한다. 미래 시점의 값은 관측에 포함하지 않는다.

env.observe()의 candidateFeatures는 최대 후보 수 × 6 배열이다. 열 순서는 SNR/10, SNR 변화량/1 dB, 고도각/90, 현재 연결 여부, SNR 이력 존재 여부, 유효 후보 여부다. 빈 칸은 0으로 채우며 actionMask가 선택 가능 여부를 구분한다. satelliteIDs는 원래 위성 ID와 칸의 대응을 제공한다.

vector는 candidateFeatures(:) 뒤에 trailingLossRun/(trailingLossRun+60)을 붙인 열벡터다. 현재 시나리오 최대 13후보에서는 입력 79개다. 이 정규화는 실험 설계값이며 학습 시 동일하게 적용해야 한다.

## Reward

feedback.reward는 그 1초 동안의 결과로 계산한다.

~~~matlab
reward = w.onTime * onTimeFraction ...
       - w.burst * burstPenalty ...
       - w.handover * double(handover);
~~~

기본 가중치는 onTime=1, burst=0.5, handover=0.05다. 실험용 시작값으로 정했으며 성능을 보며 조정할 수 있다.

lost 패킷마다 연속 손실 길이 L을 증가시키고 L/(L+60)을 더한 뒤 60으로 나누어 burstPenalty를 계산한다. 정상 수신이면 L이 0이 된다. 같은 개수의 손실이어도 길게 이어질수록 더 큰 감점이 생긴다. L은 1초 경계를 넘어 이어진다. 지각 수신은 기한 내 도착 보상을 받지 못하며 최종 미도착에 해당하는 연속 손실에는 넣지 않는다.

핸드오버로 발생한 손실도 기한 내 도착과 연속 손실 계산에 포함하며, 0.05는 빈번한 전환을 줄이기 위한 추가 비용이다. 핸드오버 횟수 자체를 평가 목표보다 우선하지 않도록 가중치를 비교해야 한다. rewardDetails로 항목별 점수와 연속 손실 길이를 확인할 수 있다.

~~~matlab
weights = struct('onTime',1,'burst',0.5,'handover',0.05);
env = GSLRLEnvironment(weights);
~~~

현재 구현 범위는 State, Action 인터페이스와 Reward 계산이다. 학습 신경망과 Double DQN 학습 루프는 다음 연결 단계다.
