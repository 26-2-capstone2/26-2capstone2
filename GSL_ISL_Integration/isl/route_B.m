% B 라우팅 결정 - 링크 점유율 L로 주/대체/우회 경로 중 다음 방향을 고름 (나중에 강화학습으로 반영할 파일)
%
function [nextDir, choiceType, L, N] = route_B(curP, curS, queueLen, G, P)
% B: 트래픽 부하 고려 라우팅 (Liu et al. 단순화)
% 입력: 현재 위성 (curP,curS) 1-based, 링크별 큐 길이 queueLen, 그리드 G, 설정 P
% 출력: nextDir 방향(1 상, 2 하, 3 좌, 4 우), choiceType 선택 유형(1 주, 2 대체, 3 우회)
%       L, N 4방향 링크 점유율 / 이웃 부하 (없는 방향은 -1)
% 나중에 강화학습으로 바꿀 때는 이 함수만 교체하면 됨

L = -ones(1, 4);
N = -ones(1, 4);
for d = G.validDirs{curP, curS}
    nextP = curP + G.stepP(d);
    nextS = curS + G.stepS(d);
    N(d) = mean(queueLen(G.outLinks{nextP, nextS}));     % 이웃 부하 N_n(t)
    V = queueLen(G.linkId(curP, curS, d));                % 링크 부하 V_mn(t) = q_mn(t)
    L(d) = (P.k * V + (1 - P.k) * N(d)) / P.queueMax;     % 링크 점유율 L
end

% (1) 주 경로 / 대체 경로: 좌/우 우선
remainP = G.dstSat(1) - curP;
remainS = G.dstSat(2) - curS;
if remainP ~= 0
    primaryDir = 3 + (remainP > 0);
    if remainS ~= 0
        altDir = 1 + (remainS > 0);
    else
        altDir = 0;
    end
else
    primaryDir = 1 + (remainS > 0);
    altDir = 0;
end

% (2) 링크 상태 판정, (3) 다음 홉 선택
primState = link_state(L(primaryDir), P);
if altDir > 0
    altState = link_state(L(altDir), P);
else
    altState = inf;
end

if primState == 1
    nextDir = primaryDir; choiceType = 1;
elseif primState == 2
    if altState == 1
        nextDir = altDir; choiceType = 2;
    else
        nextDir = primaryDir; choiceType = 1;
    end
else
    if altState <= 2
        nextDir = altDir; choiceType = 2;
    else
        % 둘 다 혼잡 또는 대체 경로 없음: 모든 방향 중 L 최소 (동점이면 주 > 대체 > 나머지)
        cand = [primaryDir altDir setdiff(1:4, [primaryDir altDir])];
        cand = cand(cand > 0);
        cand = cand(ismember(cand, G.validDirs{curP, curS}));
        [~, i] = min(L(cand));
        nextDir = cand(i); choiceType = 3;
    end
end
end

function state = link_state(L, P)
% 1 Idle, 2 Relatively Busy, 3 Busy
if L < P.X
    state = 1;
elseif L < P.Y
    state = 2;
else
    state = 3;
end
end
