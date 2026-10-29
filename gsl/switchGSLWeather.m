function switchGSLWeather(f,name,notifyPacket)
if nargin<3, notifyPacket=true; end
assert(isgraphics(f)); name=string(name);
B=getappdata(f,'GSLWeatherCases'); Q=B.(name); P=Q.packetTable; M=Q.packetMetrics; C=Q.config;
H=getappdata(f,'GSLPacketPlotHandles');
H.generated.YData=M.cumulativeGenerated;
H.received.YData=M.cumulativeReceived; H.lost.YData=M.cumulativeLost;
H.rollingLoss.YData=M.rollingPacketLossRatio;
H.onTime.YData=M.rollingOnTimeDeliveryRate_pct; H.late.YData=M.rollingLateRate_pct;
H.failure.YData=M.rollingDeadlineFailureRate_pct; H.rate.YData=M.rollingReceivedPacketsPerSecond;
ylim(H.lossAxes,[0 max(1,1.2*max(M.rollingPacketLossRatio))]);
H.title.String={sprintf('GSL UPLINK | %s | Deadline %.1f ms | Final outcomes by generation time',name,1000*C.gslDeadline_s), ...
    sprintf('On-time %.4f%% | Loss %.4f%% | Late %d | Three-weather summary above',M.onTimeDeliveryRate_pct,M.packetLossRatio,M.latePackets)};
names=["clear","cloudy","rainy"];
popup=getappdata(f,'GSLWeatherSelector'); popup.Value=find(names==name);
setappdata(f,'GSLSelectedWeather',name);
diag=findall(groot,'Type','figure','Tag','GSLCoreResult','Name','GSL Uplink - Channel and Loss Runs');
if numel(diag)==1
    D=getappdata(diag,'GSLDiagnosticPlotHandles');
    D.snr.YData=P.snr_dB;
    D.title.String=sprintf('GSL uplink | %s | defined meteorology + ITU absorption model',name);
    set(D.onTime,'XData',P.time_s(P.onTime),'YData',ones(sum(P.onTime),1));
    set(D.lost,'XData',P.time_s(P.lost==1),'YData',zeros(sum(P.lost==1),1));
    set(D.late,'XData',P.time_s(P.late),'YData',2*ones(sum(P.late),1));
    set(D.runs,'XData',M.lossRuns.firstGeneration_s,'YData',M.lossRuns.length_packets);
    D.statusTitle.String=sprintf('Loss %.3f%% | On-time %.3f%% | Deadline %.1f ms',M.packetLossRatio,M.onTimeDeliveryRate_pct,1000*C.gslDeadline_s);
    D.runTitle.String=sprintf('%d loss runs | max %d | mean %.2f packets',M.lossRunCount,M.maxConsecutiveLoss,M.meanConsecutiveLoss);
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
