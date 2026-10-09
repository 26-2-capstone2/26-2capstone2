function verify_handover_playback()
% Actual native playback with full constellation and real handover regression.
C=configGSL(); C.duration_s=110; C.makePlots=false; C.exportResults=false;
C.viewerPlaybackSpeed=20; C.autoPlay3D=false;
R=main_gsl_simulation(C);
guard=onCleanup(@()delete(R.viewerController)); %#ok<NASGU>
assert(R.scenario.AutoSimulate && numel(R.satellites)==1584);
assert(R.config.gsLatitude_deg==37 && R.config.gsLongitude_deg==128);
playGSL(R); deadline=tic;
while seconds(R.viewer.CurrentTime-R.scenario.StartTime)<110-1e-6
    assert(toc(deadline)<180,'GSL:PlaybackTimeout','Native full-constellation playback stalled.');
    pause(.05);
end
R.viewerController.refresh();
assert(R.viewerController.StateIndex==111);
fprintf('PASS: native continuous playback through real handovers; 1584 satellites; Korean GS 37N/128E.\n');
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
    assert(abs(seconds(R.viewer.CurrentTime-R.scenario.StartTime)-R.linkState.time_s(k))<1e-8);
    fprintf('PASS: actual manual position+color handover t=%g, gray old=%d, red new=%d.\n', ...
        R.linkState.time_s(k),old,new);
end
R.viewerController.setTime(110); delete(R.viewerController);
fprintf('PASS: native viewer handover regression; native widgets enabled.\n');
end
