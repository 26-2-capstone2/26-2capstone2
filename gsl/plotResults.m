function F=plotResults(L,P,M,CFG)
% Native viewer plus two figures; physical data stay in CSV/MAT.
old=findall(groot,'Type','figure','Tag','GSLCoreResult');
if ~isempty(old), close(old); end
F=gobjects(0); events=L.time_s(L.handoverEvent);
gs=sprintf('GS %.4f N, %.4f E, %g m',CFG.gsLatitude_deg,CFG.gsLongitude_deg,CFG.gsAltitude_m);
f=figure('Name','GSL Serving / Handover Summary','NumberTitle','off', ...
    'Color','w','Tag','GSLCoreResult','Position',[100 80 1100 700]);
tl=tiledlayout(f,2,1); tl.OuterPosition=[0 0.08 1 0.92];
nexttile; ids=unique([0;L.servingSatID]); [~,row]=ismember(L.servingSatID,ids);
stairs(L.time_s,row,'LineWidth',1.4); yticks(1:numel(ids));
labels=string(ids); labels(ids==0)="0 (none)"; yticklabels(labels);
ylim([0.5 numel(ids)+0.5]); ylabel('Serving ID (categorical)'); grid on; mark(events);
nexttile; stairs(L.time_s,L.visibleCount,'LineWidth',1.4); hold on;
out=~L.isLinkAvailable;
plot(L.time_s(out),zeros(sum(out),1),'rx','DisplayName','Outage');
ylabel('Visible candidates'); xlabel('Time [s]'); grid on; mark(events);
sgtitle(tl,{'GSL Serving / Handover Summary',gs});
saveFigure(f,'serving_handover.png',CFG); F(end+1)=f;
if isempty(P), return; end
f=figure('Name','Packet Transmission Performance','NumberTitle','off','Color','w', ...
    'Tag','GSLCoreResult','Position',[120 60 1100 850]);
tl=tiledlayout(f,3,1);
nexttile; plot(P.time_s,M.cumulativeGenerated,'-','LineWidth',2); hold on;
plot(P.time_s,M.cumulativeAttempted,'--','LineWidth',1.6);
plot(P.time_s,M.cumulativeReceived,':','LineWidth',1.5);
plot(P.time_s,M.cumulativeLost,'-.','LineWidth',1.5);
legend('Generated','Attempted',label('Received',M.receivedPackets),label('Lost',M.lostPackets),'Location','northwest');
ylabel('Cumulative packets'); grid on; mark(events);
nexttile; plot(P.time_s,M.rollingFailureRatio,'LineWidth',1.4);
ylabel('Failure / Generated [%]'); ylim([0 100]); grid on; mark(events);
title(sprintf('%g-second rolling window: lost / generated',M.window_s));
nexttile; plot(P.time_s,M.rollingReceivedPacketsPerSecond,'LineWidth',1.4);
ylabel('Received packets/s'); xlabel('Time [s]'); ylim([0 CFG.packetRate_pps*1.1]); grid on; mark(events);
title('Rolling received throughput (partial window at startup)');
for ax=findall(f,'Type','axes').', xlim(ax,[0 CFG.duration_s]); end
sgtitle(tl,{'Packet Transmission Performance',gs,CFG.perModelSource},'Interpreter','none');
if M.pendingPackets>0
    annotation(f,'textbox',[.12 .01 .85 .03],'String', ...
        sprintf('%d unresolved attempts: totals/affected windows are N/A',M.pendingPackets), ...
        'EdgeColor','none','Color',[.7 .1 .1]);
end
saveFigure(f,'packet_performance.png',CFG); F(end+1)=f;
end
function s=label(name,value)
if isnan(value), s=[name ' (N/A)']; else, s=name; end
end
function mark(times)
for t=times.', xline(t,'--','Color',[.55 .55 .55],'HandleVisibility','off'); end
end
function saveFigure(f,name,C)
if C.exportResults, exportgraphics(f,fullfile(C.outputDir,name),'Resolution',150); end
end
