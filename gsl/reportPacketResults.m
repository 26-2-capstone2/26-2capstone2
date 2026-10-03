function reportPacketResults(L,P,M,CFG)
P.rolling_failure_ratio_pct=M.rollingFailureRatio;
P.rolling_loss_ratio_pct=M.rollingFailureRatio; % compatibility alias, GENERATED denominator
P.rolling_success_ratio_pct=M.rollingSuccessRatio;
P.rolling_received_pps=M.rollingReceivedPacketsPerSecond;
P.cumulative_generated=M.cumulativeGenerated; P.cumulative_attempted=M.cumulativeAttempted;
P.cumulative_transmitted=M.cumulativeTransmitted; P.cumulative_received=M.cumulativeReceived;
P.cumulative_lost=M.cumulativeLost; P.cumulative_outage_loss=M.cumulativeOutageLoss;
P.cumulative_link_loss=M.cumulativeLinkLoss;
width=max(0,min(L.time_s(2:end),CFG.duration_s)-L.time_s(1:end-1));
M.totalOutageDuration_s=sum(width.*double(~L.isLinkAvailable(1:end-1)));
summary=sprintf(['===== GSL Simulation Summary =====\nTime: %g s | GS: %.4f N, %.4f E, %g m\n' ...
    'UDP: %g Bytes | %g packets/s\nPacket model: %s\n' ...
    'Generated: %d\nAttempted: %d\nReceived: %s\nLost (total): %s\n' ...
    'Overall failure (Lost/Generated): %s\nOutage loss: %d\nLink loss: %s\n' ...
    'Pending: %d\nHandovers: %d\nOutage duration: %g s\n' ...
    'Average success (Received/Generated): %s\nAverage received: %s packets/s\n' ...
    '==================================\n'],CFG.duration_s,CFG.gsLatitude_deg,CFG.gsLongitude_deg,CFG.gsAltitude_m, ...
    CFG.packetSize_bytes,CFG.packetRate_pps,CFG.perModelSource,M.generatedPackets,M.attemptedPackets, ...
    number(M.receivedPackets),number(M.lostPackets),pct(M.packetLossRatio),M.outageLossPackets, ...
    number(M.linkLossPackets),M.pendingPackets,sum(L.handoverEvent),M.totalOutageDuration_s, ...
    pct(M.averageSuccessRate_pct),number(M.averageReceivedPacketsPerSecond));
fprintf('%s',summary);
if CFG.exportResults
    if ~isfolder(CFG.outputDir), mkdir(CFG.outputDir); end
    writetable(P,fullfile(CFG.outputDir,'packet_results.csv'));
    writetable(L,fullfile(CFG.outputDir,'link_state.csv'));
    save(fullfile(CFG.outputDir,'packet_results.mat'),'P','M','L','CFG','-v7');
    fid=fopen(fullfile(CFG.outputDir,'packet_summary.txt'),'w','n','UTF-8');
    assert(fid>=0); guard=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s',summary);
    obsolete={'visibility.png','environment_3d.png','link_state.png', ...
        'link_performance.png','cumulative_packets.png','rolling_packet_loss.png'};
    for i=1:numel(obsolete)
        path=fullfile(CFG.outputDir,obsolete{i}); if isfile(path), delete(path); end
    end
end
if CFG.makePlots, plotResults(L,P,M,CFG); end
end
function s=number(v)
if isnan(v), s='N/A'; else, s=sprintf('%g',v); end
end
function s=pct(v)
if isnan(v), s='N/A'; else, s=sprintf('%.3f %%',v); end
end
