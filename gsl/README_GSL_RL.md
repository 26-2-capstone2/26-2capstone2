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
done = false;

while ~done
    action = 0;
    if ~isempty(candidates)
        action = 1;  % 연결 예시. 매초 SNR이 가장 높은 후보 선택.
    end
    [candidates, feedback, done, packets] = env.step(action);
end

[packetTable, metrics] = env.results();
disp(metrics.lossRuns)
~~~

## 팀원 코드와 주고받는 값

| 항목 | 내용 |
| --- | --- |
| candidates | time_s, rank, satelliteID, snr_dB, elevation_deg, isServing |
| action | 현재 Table의 1부터 시작하는 순위. 후보가 없을 때만 0을 전달 |
| feedback | 해당 1초의 생성·수신·원인별 손실·기한 내 도착·지각 도착 개수, 핸드오버 여부, 끝에서 이어지는 손실 길이와 지금까지의 최대 연속 손실 |
| packets | 해당 구간의 원본 패킷 ID, 위성 ID, 손실 원인, 지연 및 도착 시각 등 |
| done | 600초 구간 처리가 끝나면 true. 이후 results()로 전체 결과 확인 |

후보 순위는 매초 달라질 수 있다. 순위의 숫자가 달라도 실제 위성 ID가 같으면 연결을 유지한다. Table에 포함된 시각은 현재 결정 시점이다. 후보 수는 매초 달라지며 env.maxCandidateCount로 기본 시나리오의 최대 후보 수를 확인할 수 있다. Double DQN 입력용 배열 크기, 빈 칸 마스크, 보상 구성은 학습 코드에서 정한다.

verify_gsl_rl을 실행하면 기존 위성 선택 규칙을 강화학습 환경으로 재생해 36,000개 패킷 결과가 일치하는지 검사한다. 별도로 외부 위성 선택, 잘못된 순위 거부, 핸드오버 반영을 확인한다.
