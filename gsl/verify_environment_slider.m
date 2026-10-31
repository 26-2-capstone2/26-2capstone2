function verify_environment_slider
% Actual default entry point, no globe, absolute loss callbacks and clock.
C=configGSL(); C.duration_s=6; C.exportResults=false; C.openPacketViewer=true;
R=main_gsl_simulation(C);
assert(isempty(R.viewer) && ~isfield(R,'viewerController'));
assert(~isfield(R,'weatherResults'));
f=R.attenuationResultsFigure; pv=R.packetViewer;
d=findall(groot,'Name','GSL Uplink - Channel and Loss Runs');
D=getappdata(d,'GSLDiagnosticPlotHandles');
guard=onCleanup(@()delete(pv)); %#ok<NASGU>
assert(isempty(findall(f,'Tag','GSLWeatherSelector')));
pv.setTime(1.25); count=numel(findall(groot,'Type','figure'));
s=findall(f,'Tag','GSLAttenuationSlider'); last=[];
for value=[0 2 4 8 8.2 12 20]
    s.Value=value; cb=s.Callback; cb(s,[]);
    B=getappdata(f,'GSLWeatherCases'); Q=B.manual;
    assert(Q.config.environmentLoss_dB==value);
    assert(all(abs(Q.linkState.snr_dB-(Q.linkState.vacuumSNR_dB-value))<1e-10 | ~Q.linkState.isLinkAvailable));
    assert(all(Q.linkState.atmosphericLoss_dB==value));
    assert(all(Q.linkState.gasLoss_dB==0 & Q.linkState.cloudLoss_dB==0 & Q.linkState.rainLoss_dB==0));
    assert(pv.CurrentTime_s==1.25 && contains(pv.WeatherName,'Environment'));
    assert(numel(findall(groot,'Type','figure'))==count);
    assert(Q.packetMetrics.pendingPackets==0 && isfinite(Q.packetMetrics.packetLossRatio));
    assert(isequaln(D.snr.YData(:),Q.packetTable.snr_dB));
    assert(isequaln(D.lost.XData(:),Q.packetTable.time_s(Q.packetTable.lost==1)));
    assert(isequaln(D.onTime.XData(:),Q.packetTable.time_s(Q.packetTable.onTime)));
    assert(isequaln(D.runs.YData(:),Q.packetMetrics.lossRuns.length_packets));
    if ~isempty(last), assert(isequal(last,Q.packetTable.phyRandomDraw)); end
    last=Q.packetTable.phyRandomDraw;
end
fprintf('PASS environment slider: actual main, no globe/weather table, absolute attenuation, paired draws, fixed playback time.\n');
end
