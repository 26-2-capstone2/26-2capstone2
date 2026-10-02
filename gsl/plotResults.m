function F = plotResults(L,P,M,CFG)
% Core research figures only; intermediate variables remain in data exports.
F=gobjects(0);
old=findall(groot,'Type','figure','Tag','GSLCoreResult');
if ~isempty(old), close(old); end
events=L.time_s(L.handoverEvent);
gs=sprintf('GS %.4f deg N, %.4f deg E, %g m (WGS84)', ...
    CFG.gsLatitude_deg,CFG.gsLongitude_deg,CFG.gsAltitude_m);
f=coreFigure('GSL Serving Satellite and Handover',720);
tiledlayout(2,1);
nexttile; plot(L.time_s,L.elevation_deg,'LineWidth',1.4); hold on;
yline(CFG.minElevation_deg,'--',sprintf('Minimum %g deg',CFG.minElevation_deg));
ylabel('Serving elevation [deg]'); grid on; markHandovers(events);
nexttile;
% ID is nominal, not a physical magnitude: show exact IDs on an equal-spaced axis.
ids=unique([0;L.servingSatID]); [~,row]=ismember(L.servingSatID,ids);
stairs(L.time_s,row,'LineWidth',1.4); yticks(1:numel(ids));
labels=string(ids); labels(ids==0)="0 (none)"; yticklabels(labels);
ylim([0.5 numel(ids)+0.5]); ylabel('Satellite ID (categorical)');
xlabel('Time [s]'); grid on; markHandovers(events);
sgtitle({'GSL Serving Satellite and Handover',gs});
saveFigure(f,'serving_handover.png',CFG); F(end+1)=f;
f=coreFigure('GSL Link Performance',640); tiledlayout(2,1);
nexttile; plot(L.time_s,L.propagationDelay_ms,'LineWidth',1.4);
ylabel('One-way delay [ms]'); grid on; markHandovers(events);
nexttile; plot(L.time_s,L.snr_dB,'LineWidth',1.4);
ylabel('SNR [dB]'); xlabel('Time [s]'); grid on; markHandovers(events);
sgtitle({'GSL Link Performance',gs});
saveFigure(f,'link_performance.png',CFG); F(end+1)=f;
if isempty(P), return; end
f=coreFigure('Cumulative UDP Packet Transmission',540);
plot(P.time_s,M.cumulativeGenerated,'-','LineWidth',2); hold on;
plot(P.time_s,M.cumulativeTransmitted,'--','LineWidth',1.5);
plot(P.time_s,M.cumulativeReceived,':','LineWidth',1.5);
plot(P.time_s,M.cumulativeLost,'-.','LineWidth',1.5);
legend('Generated','Transmitted',label('Received',M.receivedPackets), ...
    label('Lost',M.lostPackets),'Location','northwest');
xlabel('Time [s]'); ylabel('Number of Packets'); grid on;
xlim([0 CFG.duration_s]); title({'Cumulative UDP Packet Transmission',gs});
if M.pendingPackets>0
    text(0.98,0.07,sprintf('Received / Lost = N/A | %d pending | PER model required',M.pendingPackets), ...
        'Units','normalized','HorizontalAlignment','right','Color',[0.65 0.15 0.05]);
end
saveFigure(f,'cumulative_packets.png',CFG); F(end+1)=f;
% No empty/0% loss figure when a validated PER model is unavailable.
if any(isfinite(M.rollingPacketLossRatio))
    f=coreFigure('Rolling Packet Loss Ratio',440);
    plot(P.time_s,M.rollingPacketLossRatio,'LineWidth',1.4);
    grid on; xlim([0 CFG.duration_s]); ylim([0 100]);
    xlabel('Time [s]'); ylabel('Packet Loss Ratio [%]');
    title({sprintf('Rolling Packet Loss Ratio (%g-second window)',M.window_s),gs});
    markHandovers(events); saveFigure(f,'rolling_packet_loss.png',CFG); F(end+1)=f;
end
end
function f=coreFigure(name,height)
f=figure('Name',name,'NumberTitle','off','Color','w','Tag','GSLCoreResult', ...
    'Position',[100 80 1100 height]);
end
function s=label(name,value)
if isnan(value), s=[name ' (N/A: PER required)']; else, s=name; end
end
function markHandovers(times)
for t=times.', xline(t,'--','Color',[0.55 0.55 0.55],'HandleVisibility','off'); end
end
function saveFigure(f,name,CFG)
if CFG.exportResults, exportgraphics(f,fullfile(CFG.outputDir,name),'Resolution',150); end
end
