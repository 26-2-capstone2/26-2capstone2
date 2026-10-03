function verify_main_playback_entry()
% Main must WAIT; exercising the actual displayed button callback starts playback.
C=configGSL(); assert(C.duration_s==600 && ~C.autoPlay3D);
C.duration_s=2; C.numPlanes=4; C.satsPerPlane=6; C.phaseFactor=1;
C.makePlots=false; C.exportResults=false; C.viewerPlaybackSpeed=1000;
R=main_gsl_simulation(C);
assert(isa(R.viewerController,'GSLManualViewerController'));
assert(~R.scenario.AutoSimulate && R.viewerController.StateIndex==1);
assert(R.viewer.CurrentTime==C.startTime);
pause(.2); assert(R.viewer.CurrentTime==C.startTime); % no autoplay
b=findall(R.playbackControlFigure,'Tag','GSLPlayButton'); assert(numel(b)==1);
cb=get(b,'Callback'); cb(b,[]); % SAME callback as clicking the visible Play button
assert(R.viewerController.StateIndex==3);
assert(seconds(R.viewer.CurrentTime-C.startTime)==2);
assert(~getappdata(R.playbackControlFigure,'GSLPlaying'));
delete(R.viewerController); close(R.playbackControlFigure);
fprintf('PASS: default 600s configuration waits at t=0.\n');
fprintf('PASS: actual Play button callback starts synchronized movement and finishes the timeline.\n');
end
