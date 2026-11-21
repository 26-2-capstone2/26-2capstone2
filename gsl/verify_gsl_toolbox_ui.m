function verify_gsl_toolbox_ui()
root=fileparts(mfilename('fullpath')); out=fullfile(root,'results_toolbox_phy','ui_validation');
if ~isfolder(out),mkdir(out);end
prior=get(groot,'defaultFigureVisible'); set(groot,'defaultFigureVisible','off');
guard=onCleanup(@()set(groot,'defaultFigureVisible',prior)); %#ok<NASGU>
C=configGSLToolboxPHY(); C.makePlots=true; C.exportResults=false; C.openPacketViewer=true;
R=main_gsl_simulation(C); f=R.attenuationResultsFigure;
fprintf('Performance figure name: %s\n',f.Name);
controls=findall(f,'Type','uicontrol'); disp(get(controls,{'Tag','Style'}));
for loss=[0 8 20]
    updateGSLAttenuation(f,loss); B=getappdata(f,'GSLWeatherCases'); Q=B.manual;
    assert(Q.packetMetrics.pendingPackets==0 && height(Q.packetTable)==36000);
    text=findall(f,'Tag','GSLAttenuationStatus');
    assert(numel(text)==1,'GSL:StatusControlMissing');
    statusLines=string(text.String);
    assert(any(contains(statusLines(:),'TOOLBOX PHY')) && ~any(contains(statusLines(:),'ZERO_CWER')));
    assert(all(Q.packetTable.phyStatus(Q.packetTable.attempted)=="TOOLBOX_QPSK_AR4JA_AWGN_EMPIRICAL"));
    R.packetViewer.setTime(600);
    assert(R.packetViewer.CurrentTime_s==600);
    fprintf('UI slider %.1f dB PASS: PLR %.4f%%, on-time %.4f%%, max run %d\n', ...
        loss,Q.packetMetrics.packetLossRatio,Q.packetMetrics.onTimeDeliveryRate_pct,Q.packetMetrics.maxConsecutiveLoss);
end
updateGSLAttenuation(f,8); R.packetViewer.setTime(600);
exportapp(f,fullfile(out,'performance_8dB.png'));
exportgraphics(findall(groot,'Name','GSL Uplink - Channel and Loss Runs'), ...
    fullfile(out,'loss_runs_8dB.png'),'Resolution',140);
exportapp(R.packetViewer.Figure,fullfile(out,'packet_viewer_8dB.png'));
fprintf('TOOLBOX UI AND SLIDER CHECK PASS\n');
delete(R.packetViewer); close all;
end
