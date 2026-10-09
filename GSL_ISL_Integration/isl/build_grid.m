% 6x6 Grid 생성 - 위성 좌표, 상/하/좌/우 링크, 링크별 지연·다음 위성을 만듦
%
function G = build_grid(P)
% 6x6 Grid 링크 구조 생성 (Grid 끝은 반대편과 연결하지 않음)
% 방향 번호: 1 상(s-1), 2 하(s+1), 3 좌(p-1), 4 우(p+1)
% 내부 좌표는 1-based (문서 좌표 + 1)

G.stepP = [0 0 -1 1];       % 방향별 p 변화량
G.stepS = [-1 1 0 0];       % 방향별 s 변화량
G.numLinks = P.numPlanes * P.satsPerPlane * 4;
G.linkId = reshape(1:G.numLinks, P.numPlanes, P.satsPerPlane, 4);   % 링크 번호 = (p,s,방향)

G.hasLink = false(P.numPlanes, P.satsPerPlane, 4);   % 그 방향에 링크가 있는지
G.nextP = zeros(G.numLinks, 1);       % 링크 끝 위성 p
G.nextS = zeros(G.numLinks, 1);       % 링크 끝 위성 s
G.linkDelay = zeros(G.numLinks, 1);   % 링크 지연 (step)
G.validDirs = cell(P.numPlanes, P.satsPerPlane);   % 위성별 갈 수 있는 방향 목록
G.outLinks = cell(P.numPlanes, P.satsPerPlane);    % 위성별 나가는 링크 번호 목록

for p = 1:P.numPlanes
    for s = 1:P.satsPerPlane
        for d = 1:4
            np = p + G.stepP(d);
            ns = s + G.stepS(d);
            if np >= 1 && np <= P.numPlanes && ns >= 1 && ns <= P.satsPerPlane
                G.hasLink(p, s, d) = true;
                l = G.linkId(p, s, d);
                G.nextP(l) = np;
                G.nextS(l) = ns;
                G.linkDelay(l) = P.linkDelay(d);
            end
        end
        G.validDirs{p, s} = find(squeeze(G.hasLink(p, s, :)))';
        G.outLinks{p, s} = reshape(G.linkId(p, s, G.validDirs{p, s}), 1, []);
    end
end

G.srcSat = P.srcSat + 1;
G.dstSat = P.dstSat + 1;
end
