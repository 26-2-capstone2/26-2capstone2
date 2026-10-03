function playGSL(R,controlFigure)
% Sequential native time/style updates; avoids reentrant background timers.
assert(isfield(R,'viewerController') && isvalid(R.viewerController) && isvalid(R.viewer), ...
    'GSL:NoViewer','Run with CFG.openViewer=true first.');
if nargin<2, controlFigure=[]; end
if ~isempty(controlFigure)
    if getappdata(controlFigure,'GSLPlaying'), return; end
    setappdata(controlFigure,'GSLPlaying',true);
    setappdata(controlFigure,'GSLPlaybackStop',false);
    guard=onCleanup(@()finish(controlFigure)); %#ok<NASGU>
end
step=R.config.channelUpdateStep_s/R.config.viewerPlaybackSpeed;
start_s=seconds(R.viewer.CurrentTime-R.scenario.StartTime);
if start_s>=R.linkState.time_s(end), start_s=0; end
for t=R.linkState.time_s(R.linkState.time_s>=start_s).'
    if ~isvalid(R.viewer), break; end
    if ~isempty(controlFigure) && (~isgraphics(controlFigure) || getappdata(controlFigure,'GSLPlaybackStop')), break; end
    R.viewerController.setTime(t); pause(step);
end
end
function finish(f)
if isgraphics(f), setappdata(f,'GSLPlaying',false); end
end
