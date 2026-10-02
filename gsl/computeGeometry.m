function G = computeGeometry(sc, sats, gs, links, CFG)
% Toolbox outputs: rows=satellites, columns=time samples.
% Stored arrays: rows=time samples, columns=satellite indices.
[~,el,range,t] = aer(gs,sats);
[status,accessTime] = accessStatus(links);
assert(isequal(t,accessTime),'GSL:TimeMismatch','AER/access time mismatch.');
assert(isequal(size(el),size(status)),'GSL:ShapeMismatch','AER/access shape mismatch.');
G.timeUTC = t(:);
G.time_s = seconds(G.timeUTC-sc.StartTime);
G.satelliteIndex = (1:numel(sats)).'; % stable indices in returned Walker array
G.satelliteName = strings(numel(sats),1);
for k = 1:numel(sats)
    G.satelliteName(k) = string(sats(k).Name);
end
G.elevation_deg = el.';
G.slantRange_m = range.'; % geometric output only; no delay model in Stage 1
G.isVisible = G.elevation_deg >= CFG.minElevation_deg;
G.accessStatus = logical(status.');
% For positive elevation and no other constraints these must agree.
awayFromBoundary = abs(G.elevation_deg-CFG.minElevation_deg) > 1e-8;
assert(~any(G.isVisible(awayFromBoundary) ~= G.accessStatus(awayFromBoundary)), ...
    'GSL:VisibilityMismatch','Elevation mask disagrees with Toolbox access.');
G.visibleCount = sum(G.isVisible,2);
G.hasCandidate = G.visibleCount > 0; % visibility only, not an established link
G.maxElevation_deg = max(G.elevation_deg,[],2); % no serving selection
[p0,~] = states(sats,sc.StartTime,'CoordinateFrame','ecef');
[p1,~] = states(sats,sc.StopTime,'CoordinateFrame','ecef');
G.positionStartECEF_m = reshape(p0,3,[]);
G.positionEndECEF_m = reshape(p1,3,[]);
assert(all(isfinite(G.elevation_deg(:))) && all(G.slantRange_m(:)>0), ...
    'GSL:InvalidGeometry','Invalid geometry output.');
end
