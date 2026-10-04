% 성능 평가 지표 계산 - 시뮬레이션 결과로 지표 7개와 손실 원인별 개수를 계산
%
function M = compute_metrics(R, P)
% 성능 평가 지표 7개 + 손실 원인별 개수

status = R.status;
onTime = status == 1;                     % 기한 내 도착
reachedDst = status == 1 | status == 2;   % 목적지에 도착한 패킷 (기한 초과 포함)

M.genRate = R.genRate;
M.epsilon = R.epsilon;
M.generated = R.numPackets;
M.onTime = sum(onTime);
M.lateAtDst = sum(status == 2);
M.lateMid = sum(status == 3);
M.overflow = sum(status == 4);
M.ttlExpired = sum(status == 5);

% Average Latency: 도착 패킷의 (종료 - 생성) 평균 [논문 식 13]
M.avgLatency_ms = mean(R.endTime(reachedDst) - R.genTime(reachedDst)) * P.stepTime * 1e3;

% Packet Loss Rate: 손실 수 / 생성 수 [논문 식 14]
M.lossRate = (R.numPackets - sum(onTime)) / R.numPackets;

% Throughput: 성공 수 x 패킷 크기 / 시뮬레이션 시간 [논문 식 15], 시간 = 생성 기간
M.throughput_Mbps = sum(onTime) * P.packetSize * 8 / (P.simTime * P.stepTime) / 1e6;

% On-time Delivery Rate
M.onTimeRate = sum(onTime) / R.numPackets;

% Consecutive Packet Loss Length: 패킷 id 순서로 연속 손실 최대 길이
edge = diff([0; ~onTime; 0]);
runLengths = find(edge == -1) - find(edge == 1);
if isempty(runLengths)
    M.maxConsecLoss = 0;
else
    M.maxConsecLoss = max(runLengths);
end

% Route Change Count: 도착 패킷끼리 id 순서로 직전 패킷과 경로가 다른 횟수
D = R.decisionLog(R.decisionLog(:, 24) == 1, :);
D = sortrows(D, [2 3]);
pktIdx = D(:, 2) + 1;
satNode = D(:, 4) * P.satsPerPlane + D(:, 5);
paths = cell(R.numPackets, 1);
first = [1; find(diff(pktIdx)) + 1];
last = [first(2:end) - 1; numel(pktIdx)];
for j = 1:numel(first)
    paths{pktIdx(first(j))} = satNode(first(j):last(j));
end
reachedIds = find(reachedDst);
numChanges = 0;
for j = 2:numel(reachedIds)
    if ~isequal(paths{reachedIds(j)}, paths{reachedIds(j-1)})
        numChanges = numChanges + 1;
    end
end
M.routeChanges = numChanges;

% Average Hop Count: 도착 패킷의 홉 수 평균
M.avgHops = mean(R.hops(reachedDst));
end
