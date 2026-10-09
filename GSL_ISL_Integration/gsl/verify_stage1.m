function verify_stage1()
% Run full reference case, verify numerical invariants and viewer time change.
CFG = configGSL();
CFG.enablePackets = false; % retain the original geometry regression test
timer = tic;
R = main_gsl_simulation(CFG);
G = R.geometry;
assert(numel(R.satellites)==1584);
assert(isequal(size(G.elevation_deg),[601 1584]));
assert(all(diff(G.time_s)==1));
assert(all(G.elevation_deg(:)>=-90 & G.elevation_deg(:)<=90));
assert(isequal(G.isVisible,G.accessStatus));
movement_m = vecnorm(G.positionEndECEF_m-G.positionStartECEF_m);
assert(all(movement_m > 1000),'Satellites did not move.');
assert(any(G.isVisible(:)) && any(~G.isVisible(:)));
assert(any(diff(G.isVisible,1,1)~=0,'all'),'No visibility changes observed.');
% Circular two-body orbit has constant geocentric radius in ECEF too.
radius_m = CFG.earthEquatorialRadius_m+CFG.satAltitude_m;
assert(max(abs(vecnorm(G.positionStartECEF_m)-radius_m))<1);
assert(max(abs(vecnorm(G.positionEndECEF_m)-radius_m))<1);
R.viewer.CurrentTime = R.scenario.StartTime+seconds(60);
drawnow;
assert(R.viewer.CurrentTime==R.scenario.StartTime+seconds(60));
R.viewer.CurrentTime = R.scenario.StartTime;
drawnow;
fprintf('PASS: full constellation, time grid, motion, radius, visibility and viewer time update.\n');
fprintf('Elapsed: %.1f s. Minimum endpoint displacement: %.1f km.\n',toc(timer),min(movement_m)/1e3);
% Disconnected edge case: no satellite is exactly overhead at this fixed epoch.
edgeCFG = CFG;
edgeCFG.duration_s = 2; edgeCFG.minElevation_deg = 90;
edgeCFG.openViewer = false; edgeCFG.makePlots = false; edgeCFG.exportResults = false;
edge = main_gsl_simulation(edgeCFG);
assert(~any(edge.geometry.hasCandidate));
fprintf('PASS: 90-degree mask returns zero candidates without an error.\n');
end
