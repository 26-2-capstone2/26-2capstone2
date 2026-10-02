function playGSL(R)
% Frame-synchronized playback; close the viewer to stop.
% Use this entry point, not native Play, to synchronize active-link colors.
assert(isfield(R,'viewerController') && isvalid(R.viewerController), ...
    'GSL:NoViewer','Run with CFG.openViewer=true first.');
step=R.config.channelUpdateStep_s/R.config.viewerPlaybackSpeed;
for t=R.linkState.time_s.'
    if ~isvalid(R.viewer), break; end
    R.viewerController.setTime(t);
    pause(step);
end
end
