function reportPacketResults(L,P,M,CFG)
P.rolling_loss_ratio_pct=M.rollingPacketLossRatio;
P.rolling_failure_ratio_pct=M.rollingPacketLossRatio;
P.rolling_success_ratio_pct=M.rollingSuccessRatio;
P.rolling_received_pps=M.rollingReceivedPacketsPerSecond;
P.rolling_confirmed_loss_lower_bound_pct=M.rollingConfirmedLossLowerBound_pct;
P.cumulative_generated=M.cumulativeGenerated; P.cumulative_received=M.cumulativeReceived;
P.cumulative_lost=M.cumulativeLost; P.cumulative_confirmed_loss=M.cumulativeKnownLoss;
P.cumulative_pending=M.cumulativePending; P.cumulative_outage_loss=M.cumulativeOutageLoss;
if isfield(M,'rollingOnTimeDeliveryRate_pct')
    P.rolling_on_time_delivery_rate_pct=M.rollingOnTimeDeliveryRate_pct;
    P.rolling_late_rate_pct=M.rollingLateRate_pct;
    P.rolling_deadline_failure_rate_pct=M.rollingDeadlineFailureRate_pct;
    P.cumulative_on_time_delivery_rate_pct=M.cumulativeOnTimeDeliveryRate_pct;
end
P.cumulative_handover_loss=M.cumulativeHandoverLoss; P.cumulative_phy_loss=M.cumulativePhyLoss;
width=max(0,min(L.time_s(2:end),CFG.duration_s)-L.time_s(1:end-1));
M.totalOutageDuration_s=sum(width.*double(~L.isLinkAvailable(1:end-1)));
summary=sprintf(['===== GSL UDP SESSION RESULT =====\n' ...
    'Simulation Duration: %g s\nPacket Size: %g Bytes\nPacket Rate: %g packets/s\n' ...
    'Generated Packets: %d\nReceived Packets: %s\nLost Packets: %s\n' ...
    'Overall Packet Loss Ratio: %s\nPHY Loss Packets: %s\n' ...
    'Handover Loss Packets: %d\nOutage Loss Packets: %d\n' ...
    'Total Handovers: %d\nTotal Outage Duration: %g s\nAverage Received Packets/s: %s\n' ...
    'Unresolved PHY Packets: %d\nConfirmed Lost Packets: %d\nConfirmed Loss Lower Bound: %.6f %%\n' ...
    'PHY source: %s\nNoise bandwidth: %s Hz; information rate: %s bit/s\n' ...
    '100 ms interruptions are applied only to actual serving handovers.\n' ...
    'N/A means unresolved PHY; it does not mean zero loss.\n==================================\n'], ...
    CFG.duration_s,CFG.packetSize_bytes,CFG.packetRate_pps,M.generatedPackets, ...
    number(M.receivedPackets),number(M.lostPackets),pct(M.packetLossRatio),number(M.phyLossPackets), ...
    M.handoverLossPackets,M.outageLossPackets,sum(L.handoverEvent),M.totalOutageDuration_s, ...
    number(M.averageReceivedPacketsPerSecond),M.pendingPackets,M.resolvedLostPackets, ...
    M.confirmedLossLowerBound_pct,CFG.perModelSource,number(CFG.noiseBandwidth_Hz),number(CFG.informationBitRate_bps));
fprintf('%s',summary);
if isfield(CFG,'environmentLoss_dB')
    extra=sprintf('ENVIRONMENT ATTENUATION: %.1f dB total; weather labels are illustrative assumptions.\nStrict published curve support; out-of-range PHY outcomes remain unresolved.\n',CFG.environmentLoss_dB);
    fprintf('%s',extra); summary=[summary extra];
end
if isfield(M,'onTimePackets')
    extra=sprintf(['GSL UPLINK ONLY: ground station -> first satellite\n' ...
        'Scenario: %s (uncalibrated experimental channel)\n' ...
        'GSL deadline: %g ms; On-time: %d; Late: %d\n' ...
        'On-time delivery: %.6f %%; Deadline failure: %.6f %%\n' ...
        'Loss runs: %d; maximum: %d packets; mean: %.3f packets\n' ...
        'Observation end (including final arrivals): %.6f s\n'], ...
        CFG.channelScenario,1000*CFG.gslDeadline_s,M.onTimePackets,M.latePackets, ...
        M.onTimeDeliveryRate_pct,M.deadlineFailureRate_pct,M.lossRunCount, ...
        M.maxConsecutiveLoss,M.meanConsecutiveLoss,M.observationEnd_s);
    fprintf('%s',extra); summary=[summary extra];
end
if ~isfield(CFG,'environmentLoss_dB') && isfield(CFG,'weather') && ismember(string(CFG.channelScenario),["clear","cloudy","rainy"])
    W=CFG.weather;
    extra=sprintf('Weather inputs: T=%g C, P=%g Pa, vapor=%g g/m3, cloud=%g g/m3, rain=%g mm/h\nITU P.676/840/838 layer integration; defined conditions, NOT observed weather.\n', ...
        W.surfaceTemperature_C,W.surfacePressure_Pa,W.surfaceVaporDensity_g_m3,W.cloudWaterDensity_g_m3,W.rainRate_mm_h);
    summary=[summary extra]; fprintf('%s',extra);
end
if CFG.exportResults
    if ~isfolder(CFG.outputDir), mkdir(CFG.outputDir); end
    writetable(P,fullfile(CFG.outputDir,'packet_results.csv'));
    writetable(L,fullfile(CFG.outputDir,'link_state.csv'));
    if isfield(M,'lossRuns')
        writetable(M.lossRuns,fullfile(CFG.outputDir,'loss_runs.csv'));
        delivered=P(P.received==1,{'packetID','generationTime_s','arrivalTime_s','destinationSatelliteID','onTime','latency_ms'});
        writetable(delivered,fullfile(CFG.outputDir,'isl_input_packets.csv'));
    end
    save(fullfile(CFG.outputDir,'packet_results.mat'),'P','M','L','CFG','-v7');
    fid=fopen(fullfile(CFG.outputDir,'packet_summary.txt'),'w','n','UTF-8'); assert(fid>=0);
    guard=onCleanup(@()fclose(fid)); fprintf(fid,'%s',summary); %#ok<NASGU>
    obsolete={'visibility.png','environment_3d.png','link_state.png','link_performance.png', ...
        'cumulative_packets.png','rolling_packet_loss.png'};
    for i=1:numel(obsolete)
        path=fullfile(CFG.outputDir,obsolete{i}); if isfile(path), delete(path); end
    end
end
if CFG.makePlots
    plotResults(L,P,M,CFG);
    if isfield(M,'lossRuns'), plotUplinkDiagnostics(L,P,M,CFG); end
end
end
function s=number(v)
if isnan(v), s='N/A'; else, s=sprintf('%g',v); end
end
function s=pct(v)
if isnan(v), s='N/A'; else, s=sprintf('%.6f %%',v); end
end
