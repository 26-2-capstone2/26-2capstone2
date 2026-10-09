function verify_main_playback_entry()
C=configGSL(); assert(C.duration_s==600 && ~C.autoPlay3D);
C.duration_s=5; C.numPlanes=4; C.satsPerPlane=6; C.phaseFactor=1;
C.makePlots=false; C.exportResults=false;
R=main_gsl_simulation(C);
assert(R.scenario.AutoSimulate && isa(R.viewerController,'GSLNativeViewerController'));
assert(isempty(findall(groot,'Tag','GSLPlaybackControls')));
assert(strcmp(R.viewer.Name,'3D GSL Environment'));
pause(.2); assert(R.viewer.CurrentTime==C.startTime);
delete(R.viewerController);
% Synthetic serving schedule checks timer behavior independently of selection.
L=R.linkState; L.servingSatID=[1;1;2;2;2;1]; L.isLinkAvailable(:)=true;
ctrl=GSLNativeViewerController(R.scenario,R.satellites,R.groundStation,R.access,L,C);
guard=onCleanup(@()delete(ctrl)); %#ok<NASGU>
v=ctrl.Viewer; v.CurrentTime=C.startTime+seconds(2.5);
waitUntil(@()ctrl.ServingIndex==2,20);
assert(isequal(R.satellites(1).MarkerColor,[.65 .7 .8]));
assert(isequal(R.satellites(2).MarkerColor,[1 0 0]));
v.CurrentTime=C.startTime; waitUntil(@()ctrl.ServingIndex==1,20);
v.PlaybackSpeedMultiplier=2;
play(R.scenario,'Viewer',v,'PlaybackSpeedMultiplier',2);
waitUntil(@()seconds(v.CurrentTime-C.startTime)>=2.5,20);
v.GlobeViewer.setPlaybackSpeed(5); speed=v.GlobeViewer.getPlaybackSpeed(); assert(speed.Speed==5);
waitUntil(@()seconds(v.CurrentTime-C.startTime)>=5,20);
waitUntil(@()ctrl.ServingIndex==1,20);
assert(isequal(R.satellites(2).MarkerColor,[.65 .7 .8]));
fprintf('PASS: native viewer controls enabled; no custom controls or t= title.\n');
fprintf('PASS: native continuous play, live speed property, timer follows forward/backward timeline.\n');
fprintf('PASS: timer restores old serving gray and new serving red.\n');
end
function waitUntil(test,timeout)
t=tic; while ~test(), assert(toc(t)<timeout,'GSL:TestTimeout','Native playback did not advance.'); pause(.05); end
end
