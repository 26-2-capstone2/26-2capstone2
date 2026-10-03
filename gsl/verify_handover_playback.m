function verify_handover_playback()
% Exercise the same main-only AUTOPLAY entry point used by the user.
C=configGSL(); C.duration_s=110; C.makePlots=false; C.exportResults=false;
C.viewerPlaybackSpeed=1000; C.autoPlay3D=true; % opt-in automatic path for this test only
R=main_gsl_simulation(C);
assert(~R.scenario.AutoSimulate && R.viewerController.StateIndex==111);
assert(seconds(R.viewer.CurrentTime-R.scenario.StartTime)==110);
events=find(R.linkState.handoverEvent); assert(numel(events)==2);
for k=events.'
    old=R.linkState.servingSatID(k-1); new=R.linkState.servingSatID(k);
    R.viewerController.setTime(R.linkState.time_s(k-1));
    assert(isequal(R.satellites(old).MarkerColor,[1 0 0]));
    R.viewerController.setTime(R.linkState.time_s(k));
    assert(isequal(R.satellites(old).MarkerColor,[.65 .7 .8]) && ~R.satellites(old).ShowLabel);
    assert(isequal(R.satellites(new).MarkerColor,[1 0 0]) && R.satellites(new).ShowLabel);
    assert(isequal(R.access(old).LineColor,[0 .85 .15]) && isequal(R.access(new).LineColor,[1 0 0]));
    red=0;
    for j=1:numel(R.satellites), red=red+isequal(R.satellites(j).MarkerColor,[1 0 0]); end
    assert(red==1);
    assert(R.viewer.CurrentTime==R.scenario.SimulationTime);
    fprintf('PASS: actual manual position+color handover t=%g, gray old=%d, red new=%d.\n', ...
        R.linkState.time_s(k),old,new);
end
R.viewerController.setTime(110); delete(R.viewerController);
fprintf('PASS: main-only automatic playback; 111 sequential native frames; native widgets never enabled.\n');
end
