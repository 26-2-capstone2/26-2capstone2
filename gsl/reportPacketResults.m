function reportPacketResults(L,P,M,CFG)
% Reports simulated send-time outcomes. Unknown PER is never plotted as 0%.
P.rolling_loss_ratio_pct = M.rollingPacketLossRatio;
P.cumulative_generated = M.cumulativeGenerated;
P.cumulative_transmitted = M.cumulativeTransmitted;
P.cumulative_received = M.cumulativeReceived;
P.cumulative_lost = M.cumulativeLost;
summary = sprintf(['===== UDP Packet Summary (SIMULATION) =====\n' ...
    'Reference              : Ku-band DOWNLINK\n' ...
    'Simulation Time        : %g s\nPacket Size            : %g Bytes\n' ...
    'Packet Rate            : %g packets/s\nGenerated Packets      : %d\n' ...
    'Transmitted Packets    : %d\nReceived Packets       : %s\nLost Packets           : %s\n' ...
    'Not Transmitted        : %d\nUnresolved Outcomes    : %d\n' ...
    'Packet Loss Ratio      : %s %%\nPacket Delivery Ratio  : %s %%\n' ...
    'Generated-to-Received  : %s %%\nTotal Handovers        : %d\n' ...
    'Rolling window        : %g s, (t-window,t]\n' ...
    'PER Source             : %s\n' ...
    'N/A = undefined or unresolved; this is not measured UDP traffic.\n' ...
    '==========================================\n'], ...
    CFG.duration_s,CFG.packetSize_bytes,CFG.packetRate_pps,M.generatedPackets, ...
    M.transmittedPackets,number(M.receivedPackets),number(M.lostPackets), ...
    M.notTransmittedPackets,M.pendingPackets,number(M.packetLossRatio), ...
    number(M.packetDeliveryRatio),number(M.generatedToReceivedRatio), ...
    sum(L.handoverEvent),M.window_s,string(CFG.perModelSource));
fprintf('%s',summary);
if CFG.exportResults
    if ~isfolder(CFG.outputDir), mkdir(CFG.outputDir); end
    writetable(P,fullfile(CFG.outputDir,'packet_results.csv'));
    writetable(L,fullfile(CFG.outputDir,'link_state.csv'));
    save(fullfile(CFG.outputDir,'packet_results.mat'),'P','M','L','CFG','-v7');
    fid = fopen(fullfile(CFG.outputDir,'packet_summary.txt'),'w','n','UTF-8');
    assert(fid>=0,'Cannot open summary output.');
    cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s',summary);
end
if ~CFG.makePlots, return; end
eventTimes = L.time_s(L.handoverEvent);
f = figure('Name','Serving and downlink state','Color','w','Position',[100 80 1000 720]);
tiledlayout(3,1);
nexttile; stairs(L.time_s,L.servingSatID,'LineWidth',1.2);
ylabel('Serving index (0=none)'); grid on; title('Serving Satellite / Handover');
markHandovers(eventTimes);
nexttile; plot(L.time_s,L.propagationDelay_ms,'LineWidth',1.2);
ylabel('Delay [ms]'); title('One-way Propagation Delay'); grid on;
nexttile; plot(L.time_s,L.snr_dB,'LineWidth',1.2);
ylabel('SNR [dB]'); xlabel('Time [s]'); title('Ku-band Downlink SNR'); grid on;
markHandovers(eventTimes);
saveFigure(f,'link_state.png',CFG);
f = figure('Name','Cumulative UDP Packet Transmission','Color','w','Position',[120 100 1000 540]);
plot(P.time_s,M.cumulativeGenerated,'-','LineWidth',2); hold on;
plot(P.time_s,M.cumulativeTransmitted,'--','LineWidth',1.5);
plot(P.time_s,M.cumulativeReceived,':','LineWidth',1.5);
plot(P.time_s,M.cumulativeLost,'-.','LineWidth',1.5);
legend('Generated','Transmitted',label('Received',M.receivedPackets), ...
    label('Lost',M.lostPackets),'Location','northwest');
xlabel('Time [s]'); ylabel('Number of Packets'); grid on;
xlim([0 CFG.duration_s]); title('Cumulative UDP Packet Transmission');
if M.pendingPackets>0
    text(0.98,0.08,sprintf('%d outcomes pending: PER model required',M.pendingPackets), ...
        'Units','normalized','HorizontalAlignment','right','Color',[0.65 0.15 0.05]);
end
saveFigure(f,'cumulative_packets.png',CFG);
f = figure('Name','Rolling Packet Loss Ratio','Color','w','Position',[140 120 1000 440]);
plot(P.time_s,M.rollingPacketLossRatio,'LineWidth',1.4);
grid on; xlim([0 CFG.duration_s]); ylim([0 100]);
xlabel('Time [s]'); ylabel('Packet Loss Ratio [%]');
title(sprintf('Rolling Packet Loss Ratio (%g-second window)',M.window_s));
markHandovers(eventTimes);
if ~any(isfinite(M.rollingPacketLossRatio))
    text(0.5,0.5,'N/A: PER model unavailable or no transmitted packets', ...
        'Units','normalized','HorizontalAlignment','center','BackgroundColor','w');
end
saveFigure(f,'rolling_packet_loss.png',CFG);
end
function s = number(v)
if isnan(v), s='N/A'; else, s=sprintf('%g',v); end
end
function s = label(name,value)
if isnan(value), s=[name ' (N/A: PER required)']; else, s=name; end
end
function markHandovers(times)
for t=times.', xline(t,'--','Color',[0.55 0.55 0.55],'HandleVisibility','off'); end
end
function saveFigure(f,name,CFG)
if CFG.exportResults, exportgraphics(f,fullfile(CFG.outputDir,name),'Resolution',150); end
end
