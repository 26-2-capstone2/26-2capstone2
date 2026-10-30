function F=plotResults(L,P,M,CFG)
% Session results; auxiliary RF/geometry values remain in CSV/MAT.
old=findall(groot,'Type','figure','Tag','GSLCoreResult'); if ~isempty(old), close(old); end
F=gobjects(0); events=L.time_s(L.handoverEvent);
gs=sprintf('GS %.4f N, %.4f E, %g m',CFG.gsLatitude_deg,CFG.gsLongitude_deg,CFG.gsAltitude_m);
f=figure('Name','GSL Session / Handover','NumberTitle','off','Color','w', ...
    'Tag','GSLCoreResult','Position',[100 80 1100 700]);
tl=tiledlayout(f,2,1); tl.OuterPosition=[0 .08 1 .92];
nexttile; ids=unique([0;L.servingSatID]); [~,row]=ismember(L.servingSatID,ids);
stairs(L.time_s,row,'LineWidth',1.4); yticks(1:numel(ids)); labels=string(ids); labels(ids==0)="0 (none)";
yticklabels(labels); ylim([.5 numel(ids)+.5]); ylabel('Serving satellite ID'); grid on; mark(events);
nexttile; stairs(L.time_s,L.elevation_deg,'LineWidth',1.4); hold on;
yline(CFG.minElevation_deg,':','Elevation mask','HandleVisibility','off');
ylim([0 90]); ylabel('Serving elevation [deg]'); xlabel('Time [s]'); grid on; mark(events);
sgtitle(tl,{'GSL Session / Handover',gs});
saveFigure(f,'serving_handover.png',CFG); F(end+1)=f;
if isempty(P), return; end
f=figure('Name','UDP SESSION PERFORMANCE','NumberTitle','off','Color','w', ...
    'Tag','GSLCoreResult','Position',[120 40 1100 1000]); tl=tiledlayout(f,4,1);
nexttile; H.generated=plot(P.time_s,M.cumulativeGenerated,'-','LineWidth',1.8); hold on;
H.received=plot(P.time_s,M.cumulativeReceived,':','LineWidth',1.5);
H.lost=plot(P.time_s,M.cumulativeLost,'-.','LineWidth',1.5);
H.knownReceived=plot(P.time_s,cumsum(double(P.received==1)),'--','Color',[.3 .6 .3],'LineWidth',1.1,'Visible','off');
H.knownLost=plot(P.time_s,M.cumulativeKnownLoss,'--','Color',[.6 .2 .6],'LineWidth',1.1,'Visible','off');
if M.pendingPackets>0
    plot(P.time_s,M.cumulativeKnownLoss,'--','LineWidth',1.3);
    legend('Generated','Received (N/A)','Lost (N/A)','Confirmed loss lower bound','Location','northwest');
else
    legend('Generated','Received','Lost','Location','northwest');
end
ylabel('Cumulative packets'); grid on; mark(events);
nexttile; H.rollingLoss=plot(P.time_s,M.rollingPacketLossRatio,'LineWidth',1.4); hold on;
H.lossAxes=gca;
if M.pendingPackets>0
    plot(P.time_s,M.rollingConfirmedLossLowerBound_pct,'--','LineWidth',1.4);
    legend('Total loss ratio (N/A)','Confirmed loss lower bound','Location','northeast');
end
ylabel('Lost / Generated [%]'); grid on; mark(events);
if M.pendingPackets>0
    ylim([0 max(1,1.2*max(M.rollingConfirmedLossLowerBound_pct))]);
else
    ylim([0 max(1,1.2*max(M.rollingPacketLossRatio))]);
end
title(sprintf('%g-second rolling loss / generated',M.window_s));
nexttile;
if isfield(M,'rollingOnTimeDeliveryRate_pct')
    H.onTime=plot(P.time_s,M.rollingOnTimeDeliveryRate_pct,'Color',[0 .45 .2],'LineWidth',1.6); hold on;
    H.late=plot(P.time_s,M.rollingLateRate_pct,':','Color',[.8 .4 0],'LineWidth',1.2);
    H.failure=plot(P.time_s,M.rollingDeadlineFailureRate_pct,'--','Color',[.75 .1 .1],'LineWidth',1.2);
    legend('On-time delivery','Late arrival','Deadline failure (loss + late)','Location','southwest');
    title(sprintf('%g-second window: on-time / generated (GSL deadline %.1f ms)',M.window_s,1000*CFG.gslDeadline_s));
else
    title('Deadline metrics unavailable');
end
ylabel('Packets / Generated [%]'); ylim([0 105]); grid on; mark(events);
nexttile; H.rate=plot(P.time_s,M.rollingReceivedPacketsPerSecond,'LineWidth',1.4);
ylabel('Received packets/s'); xlabel('Time [s]'); ylim([0 CFG.packetRate_pps*1.1]); grid on; mark(events);
title('Rolling successfully received packets/s');
if M.pendingPackets>0
    text(.5,.5,'N/A: receiver bandwidth / information rate not confirmed', ...
        'Units','normalized','HorizontalAlignment','center','Color',[.7 .1 .1]);
end
for ax=findall(f,'Type','axes').', xlim(ax,[0 CFG.duration_s]); end
if isfield(M,'onTimeDeliveryRate_pct')
    summary=sprintf('Overall on-time %.4f%% | Loss %.4f%% | Late %d | GSL deadline %.1f ms', ...
        M.onTimeDeliveryRate_pct,M.packetLossRatio,M.latePackets,1000*CFG.gslDeadline_s);
    H.title=sgtitle(tl,{'GSL UPLINK: PACKET DELIVERY AND DEADLINE',summary, ...
        sprintf('%s | %s | Final outcomes grouped by generation time',gs,CFG.channelScenario)},'Interpreter','none');
else
    sgtitle(tl,{'UDP SESSION PERFORMANCE',gs,CFG.perModelSource},'Interpreter','none');
end
if M.pendingPackets>0
    annotation(f,'textbox',[.12 .005 .85 .025],'String', ...
        sprintf('%d unresolved PHY packets; dashed lower bounds are not total loss.',M.pendingPackets), ...
        'EdgeColor','none','Color',[.7 .1 .1]);
end
saveFigure(f,'packet_performance.png',CFG); F(end+1)=f;
H.layout=tl; setappdata(f,'GSLPacketPlotHandles',H);
end
function mark(times)
for t=times.', xline(t,'--','Color',[.55 .55 .55],'HandleVisibility','off'); end
end
function saveFigure(f,name,C)
if C.exportResults, exportgraphics(f,fullfile(C.outputDir,name),'Resolution',150); end
end
