function verify_main_playback_entry()
C=configGSL(); C.duration_s=2; C.numPlanes=4; C.satsPerPlane=6; C.phaseFactor=1;
C.makePlots=false; C.exportResults=false; C.viewerPlaybackSpeed=1000;
R=main_gsl_simulation(C);
assert(isa(R.viewerController,'GSLManualViewerController'));
assert(~R.scenario.AutoSimulate && R.viewerController.StateIndex==3);
assert(seconds(R.viewer.CurrentTime-C.startTime)==2);
delete(R.viewerController);
fprintf('PASS: unchanged main filename loads NEW manual controller and automatically plays.\n');
end
