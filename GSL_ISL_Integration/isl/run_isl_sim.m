% 시뮬레이션 1회 실행 - 매 step(1 ms) 도착→확인→생성→라우팅→전송을 반복하고 결정 기록을 남김
%
function R = run_isl_sim(P, genRate, epsilon, randomSeed, recordAnim, externalPackets)
if nargin < 6, externalPackets = []; end
useExternal = ~isempty(externalPackets);
% 2D Grid ISL 시뮬레이션 1회 실행 (매 step = 1 ms)
% genRate: 1초마다 생성하는 패킷 수 (일정 간격), epsilon: 무작위 선택 확률 ε
% recordAnim: true면 애니메이션용 큐/전송 상태 기록
%
% 패킷 상태 status: 0 진행 중, 1 기한 내 도착, 2 목적지 기한 초과,
%                   3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

rng(randomSeed, 'twister');
G = build_grid(P);
numLinks = G.numLinks;
queueMax = P.queueMax;

% 링크별 큐 (원형 버퍼, 패킷 id 저장)
queueBuf = zeros(numLinks, queueMax);
queueHead = ones(numLinks, 1);
queueLen = zeros(numLinks, 1);

% 패킷 정보
stepsPerSec = round(1 / P.stepTime);
numNew = @(t) floor((t - 1) * genRate / stepsPerSec) - floor((t - 2) * genRate / stepsPerSec);   % t step에 생성할 개수 (t=1에 첫 패킷)
maxPackets = floor((P.simTime - 1) * genRate / stepsPerSec) + 1;
if useExternal
    maxPackets = height(externalPackets);
    % 외부 입력은 시간 오름차순이며, 고유 ID 및 최초 생성 시각을 보존한다.
    required = {'packet_id','generation_time_s','isl_entry_time_s'};
    assert(all(ismember(required, externalPackets.Properties.VariableNames)), 'Missing external packet fields');
    assert(all(diff(externalPackets.isl_entry_time_s) >= 0), 'External packets must be sorted by entry time');
    assert(numel(unique(externalPackets.packet_id)) == maxPackets, 'Duplicate packet IDs');
    entryStep = max(1, ceil(externalPackets.isl_entry_time_s / P.stepTime) + 1);
    originalGenStep = externalPackets.generation_time_s / P.stepTime + 1;
    assert(all(entryStep >= originalGenStep), 'ISL entry precedes packet generation');
    assert(all(entryStep <= P.simTime), 'ISL entry beyond simulation time');
    nextExternal = 1;
end
genTime = zeros(maxPackets, 1);   % 생성 시각
ttl = zeros(maxPackets, 1);       % 남은 TTL
hops = zeros(maxPackets, 1);      % 지금까지 홉 수
curP = zeros(maxPackets, 1);      % 현재 위성 p (전송 중이면 다음 위성)
curS = zeros(maxPackets, 1);      % 현재 위성 s
status = zeros(maxPackets, 1);    % 패킷 상태 (위 설명)
endTime = zeros(maxPackets, 1);   % 종료 step
onLink = zeros(maxPackets, 1);    % 타고 있는 링크 번호 (애니메이션용)
statusCount = zeros(1, 5);        % 상태별 누적 개수 (status = 1~5)

% 도착 예정 패킷 (도착 step별 칸, 원형)
numSlots = max(P.linkDelay) + P.processingDelay + 1;
arrivalSlot = repmat({zeros(0, 1)}, numSlots, 1);

% 결정 기록 (라우팅 결정 1번 = 1줄)
decisionLog = zeros(max(maxPackets, 1) * 12, 24);
numDecisions = 0;

maxSteps = P.simTime + P.maxDrainTime;
timeline = zeros(maxSteps, 6);   % 누적: 생성, 기한 내 도착, 목적지 기한 초과, 중간 기한 초과, 오버플로, TTL 만료
if recordAnim
    animSteps = min(P.animDuration, maxSteps);
    animQueue = zeros(numLinks, animSteps, 'uint8');      % step별 링크 큐 길이
    animInFlight = zeros(numLinks, animSteps, 'uint16');  % step별 링크 위 전송 중 패킷 수
end

numPackets = 0;
t = 0;
while true
    t = t + 1;
    if t > maxSteps
        warning('run_isl_sim:drain', 'maxDrainTime 안에 모든 패킷이 끝나지 않음');
        t = maxSteps;
        break;
    end

    % 1. 도착 처리: 홉 수 +1, TTL -1
    slot = mod(t, numSlots) + 1;
    arrived = sort(arrivalSlot{slot});
    arrivalSlot{slot} = zeros(0, 1);
    onLink(arrived) = 0;
    hops(arrived) = hops(arrived) + 1;
    ttl(arrived) = ttl(arrived) - 1;

    % 2. 목적지 확인
    atDst = curP(arrived) == G.dstSat(1) & curS(arrived) == G.dstSat(2);
    age = t - genTime(arrived);
    onTimeIds = arrived(atDst & age <= P.deadline);
    status(onTimeIds) = 1; endTime(onTimeIds) = t;
    lateIds = arrived(atDst & age > P.deadline);
    status(lateIds) = 2; endTime(lateIds) = t;

    % 3. 중간 위성 확인: 기한 초과 -> TTL 만료
    inTransit = arrived(~atDst);
    % 통합 모드에서는 Deadline 초과가 곧 손실이 아님: 늦게 도착해도 계속 전달
    overDeadline = ~useExternal & (t - genTime(inTransit) > P.deadline);
    status(inTransit(overDeadline)) = 3; endTime(inTransit(overDeadline)) = t;
    inTransit = inTransit(~overDeadline);
    ttlExpired = ttl(inTransit) <= 0;
    status(inTransit(ttlExpired)) = 5; endTime(inTransit(ttlExpired)) = t;
    inTransit = inTransit(~ttlExpired);
    statusCount = statusCount + [numel(onTimeIds), numel(lateIds), nnz(overDeadline), 0, nnz(ttlExpired)];

    % 4. 패킷 생성
    newIds = zeros(0, 1);
    if useExternal
        first = nextExternal;
        while nextExternal <= maxPackets && entryStep(nextExternal) <= t
            nextExternal = nextExternal + 1;
        end
        if nextExternal > first
            newIds = (first:nextExternal-1)';
            numPackets = nextExternal - 1;
            genTime(newIds) = originalGenStep(newIds);
            ttl(newIds) = P.ttlInit;
            hops(newIds) = 0;
            curP(newIds) = G.srcSat(1);
            curS(newIds) = G.srcSat(2);
        end
    elseif t <= P.simTime && numNew(t) > 0
        newIds = (numPackets + 1 : numPackets + numNew(t))';
        numPackets = numPackets + numNew(t);
        genTime(newIds) = t;
        ttl(newIds) = P.ttlInit;
        hops(newIds) = 0;
        curP(newIds) = G.srcSat(1);
        curS(newIds) = G.srcSat(2);
    end

    % 5. 라우팅 결정 (도착 패킷 -> 생성 패킷 순)
    toRoute = [inTransit; newIds];
    for packet_id = toRoute'
        p = curP(packet_id); s = curS(packet_id);
        [nextDir, choiceType, L, N] = route_B(p, s, queueLen, G, P);
        if epsilon > 0 && rand < epsilon
            dirs = G.validDirs{p, s};
            nextDir = dirs(randi(numel(dirs)));
            choiceType = 4;   % 무작위
        end

        link = G.linkId(p, s, nextDir);
        enqueued = queueLen(link) < queueMax;

        qNow = -ones(1, 4);
        qNow(G.validDirs{p, s}) = queueLen(G.outLinks{p, s});

        numDecisions = numDecisions + 1;
        if numDecisions > size(decisionLog, 1)
            decisionLog = [decisionLog; zeros(size(decisionLog))]; %#ok<AGROW>
        end
        decisionLog(numDecisions, :) = [t, packet_id - 1, hops(packet_id), p - 1, s - 1, qNow, L, N, ...
            G.dstSat(1) - p, G.dstSat(2) - s, P.deadline - (t - genTime(packet_id)), ttl(packet_id), ...
            nextDir, choiceType, enqueued];

        if enqueued
            pos = mod(queueHead(link) - 1 + queueLen(link), queueMax) + 1;
            queueBuf(link, pos) = packet_id;
            queueLen(link) = queueLen(link) + 1;
        else
            status(packet_id) = 4; endTime(packet_id) = t;   % 큐 오버플로
            statusCount(4) = statusCount(4) + 1;
        end
    end

    % 6. 전송: 링크마다 큐 앞쪽 최대 linkCapacity개
    for link = find(queueLen > 0)'
        n = min(queueLen(link), P.linkCapacity);
        pos = mod(queueHead(link) - 1 + (0:n-1), queueMax) + 1;
        ids = queueBuf(link, pos);
        queueHead(link) = mod(queueHead(link) - 1 + n, queueMax) + 1;
        queueLen(link) = queueLen(link) - n;
        curP(ids) = G.nextP(link);
        curS(ids) = G.nextS(link);
        arriveSlot = mod(t + G.linkDelay(link) + P.processingDelay, numSlots) + 1;
        arrivalSlot{arriveSlot} = [arrivalSlot{arriveSlot}; ids(:)];
        onLink(ids) = link;
    end

    timeline(t, :) = [numPackets, statusCount];
    if recordAnim && t <= animSteps
        animQueue(:, t) = queueLen;
        animInFlight(:, t) = accumarray(onLink(onLink > 0), 1, [numLinks 1]);
    end

    if t >= P.simTime && numPackets == sum(statusCount)   % 진행 중인 패킷 없음
        break;
    end
end

R.genRate = genRate;
if useExternal
    R.externalPacketID = externalPackets.packet_id;
    R.originalGenerationTime_s = externalPackets.generation_time_s;
    R.islEntryTime_s = externalPackets.isl_entry_time_s;
end
R.epsilon = epsilon;
R.numPackets = numPackets;
R.endStep = t;
R.genTime = genTime(1:numPackets);
R.endTime = endTime(1:numPackets);
R.hops = hops(1:numPackets);
R.status = status(1:numPackets);
R.decisionLog = decisionLog(1:numDecisions, :);
R.timeline = timeline(1:t, :);
R.grid = G;
if recordAnim
    R.animQueue = animQueue(:, 1:min(animSteps, t));
    R.animInFlight = animInFlight(:, 1:min(animSteps, t));
end
end
