function switchGSLWeather(f,name,notifyPacket)
if nargin<3, notifyPacket=true; end
assert(isgraphics(f)); name=string(name);
B=getappdata(f,'GSLWeatherCases'); Q=B.(name); P=Q.packetTable; M=Q.packetMetrics; C=Q.config;
label=name;
if isfield(C,'experimentLabel'), label=string(C.experimentLabel); end
H=getappdata(f,'GSLPacketPlotHandles');
H.generated.YData=M.cumulativeGenerated;
H.received.YData=M.cumulativeReceived; H.lost.YData=M.cumulativeLost;
if isfield(H,'knownReceived')
    H.knownReceived.YData=cumsum(double(P.received==1)); H.knownLost.YData=M.cumulativeKnownLoss;
    if M.pendingPackets>0
        H.knownReceived.Visible='on'; H.knownLost.Visible='on';
        legend(ancestor(H.generated,'axes'),[H.generated H.received H.lost H.knownReceived H.knownLost], ...
            {'Generated','Received (N/A after unknown)','Lost (N/A after unknown)','Known received lower bound','Known lost lower bound'},'Location','northwest');
    else
        H.knownReceived.Visible='off'; H.knownLost.Visible='off';
        legend(ancestor(H.generated,'axes'),[H.generated H.received H.lost],{'Generated','Received','Lost'},'Location','northwest');
    end
end
H.rollingLoss.YData=M.rollingPacketLossRatio;
H.onTime.YData=M.rollingOnTimeDeliveryRate_pct; H.late.YData=M.rollingLateRate_pct;
H.failure.YData=M.rollingDeadlineFailureRate_pct; H.rate.YData=M.rollingReceivedPacketsPerSecond;
ylim(H.lossAxes,[0 max(1,1.2*max(M.rollingPacketLossRatio))]);
H.title.String={sprintf('GSL UPLINK | %s | Deadline %.1f ms | Final outcomes by generation time',label,1000*C.gslDeadline_s), ...
    sprintf('On-time %s | Loss %s | Unresolved %d | Top table: original weather cases',percent(M.onTimeDeliveryRate_pct),percent(M.packetLossRatio),M.pendingPackets)};
names=["clear","cloudy","rainy","manual"];
popup=getappdata(f,'GSLWeatherSelector'); popup.Value=find(names==name);
setappdata(f,'GSLSelectedWeather',name);
status=findall(f,'Tag','GSLAttenuationStatus');
if ~isempty(status)
    attempted=P.attempted; x=P.ebNo_dB(attempted);
    D0=readtable(fullfile(fileparts(mfilename('fullpath')),'ar4ja_r12_k1024_cwer.csv'));
    above=sum(x>D0.ebNo_dB(end)); below=sum(x<D0.ebNo_dB(1));
    if name=="manual"
        status.String=sprintf(['MANUAL +%.1f dB | clear gas baseline only | %.0f MHz / %.0f Mbps (fixed)\n' ...
            'Eb/N0 %.2f..%.2f dB; published %.2f..%.2f dB | outside: high %d / low %d / unresolved %d\n' ...
            'PLR %s | on-time %s | known loss %d (PHY %d / HO %d / outage %d) | known max run %d\n' ...
            'PLR bounds %.3f..%.3f%%; on-time bounds %.3f..%.3f%% (uncertainty bounds, not estimates).'], ...
            C.manualExtraLoss_dB,C.noiseBandwidth_Hz/1e6,C.informationBitRate_bps/1e6, ...
            min(x),max(x),D0.ebNo_dB(1),D0.ebNo_dB(end),above,below,M.pendingPackets, ...
            percent(M.packetLossRatio),percent(M.onTimeDeliveryRate_pct),M.resolvedLostPackets, ...
            sum(P.phy_loss==1),M.handoverLossPackets,M.outageLossPackets,M.maxConsecutiveLoss, ...
            M.confirmedLossLowerBound_pct,100*(M.resolvedLostPackets+M.pendingPackets)/M.generatedPackets, ...
            100*M.onTimePackets/M.generatedPackets,100*(M.onTimePackets+M.pendingPackets)/M.generatedPackets);
    else
        status.String=sprintf(['WEATHER: %s | original comparison, not slider results\n' ...
            'Curve-external packets: high %d / low %d. Original endpoint policies are assumptions.\n' ...
            'Move slider / press Apply for strict manual evaluation; outside curve becomes unresolved.'],name,above,below);
    end
end
diag=findall(groot,'Type','figure','Tag','GSLCoreResult','Name','GSL Uplink - Channel and Loss Runs');
if numel(diag)==1
    D=getappdata(diag,'GSLDiagnosticPlotHandles');
    D.snr.YData=P.snr_dB;
    D.title.String=sprintf('GSL uplink | %s | SNR [dB]',label);
    set(D.onTime,'XData',P.time_s(P.onTime),'YData',ones(sum(P.onTime),1));
    set(D.lost,'XData',P.time_s(P.lost==1),'YData',zeros(sum(P.lost==1),1));
    set(D.late,'XData',P.time_s(P.late),'YData',2*ones(sum(P.late),1));
    if isfield(D,'unresolved')
        set(D.unresolved,'XData',P.time_s(P.outcome_pending),'YData',3*ones(sum(P.outcome_pending),1));
    end
    set(D.runs,'XData',M.lossRuns.firstGeneration_s,'YData',M.lossRuns.length_packets);
    D.statusTitle.String=sprintf('Loss %s | On-time %s | Unresolved %d | Deadline %.1f ms',percent(M.packetLossRatio),percent(M.onTimeDeliveryRate_pct),M.pendingPackets,1000*C.gslDeadline_s);
    D.runTitle.String=sprintf('%d KNOWN loss runs | max %d | mean %.2f | unresolved %d',M.lossRunCount,M.maxConsecutiveLoss,M.meanConsecutiveLoss,M.pendingPackets);
end
if notifyPacket
    packets=findall(groot,'Type','figure','Tag','GSLPacketViewer');
    if numel(packets)==1
        controller=getappdata(packets,'Controller');
        if isvalid(controller), controller.setWeatherCase(Q); end
    end
end
if C.exportResults
    exportapp(f,fullfile(C.outputDir,'packet_performance.png'));
    if numel(diag)==1, exportgraphics(diag,fullfile(C.outputDir,'uplink_channel_loss_runs.png'),'Resolution',130); end
end
end
function s=percent(v)
if isnan(v), s='N/A'; else, s=sprintf('%.4f%%',v); end
end
