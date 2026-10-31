function summary=verify_saturation_sweep(referenceL,C)
% Full slider range on one geometry, paired packet random draws.
C.exportResults=false; C.makePlots=false;
rows=cell(41,1); previous=[];
for k=1:41
    a=(k-1)/2; Q=evaluateGSLAttenuation(referenceL,C,a);
    P=Q.packetTable; M=Q.packetMetrics;
    assert(M.pendingPackets==0 && isfinite(M.packetLossRatio) && isfinite(M.onTimeDeliveryRate_pct));
    assert(M.generatedPackets==M.receivedPackets+M.lostPackets);
    assert(M.lostPackets==M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets);
    assert(all(isfinite(P.phyPER(P.attempted))));
    if ~isempty(previous), assert(all(P.lost>=previous)); end
    previous=P.lost;
    rows{k}=table(a,M.generatedPackets,M.receivedPackets,M.lostPackets,M.phyLossPackets, ...
        M.handoverLossPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss, ...
        sum(P.phyStatus=="JPL_FIGURE14_LOOKUP"),sum(P.phyStatus=="HIGH_SNR_ZERO_CWER_ASSUMPTION"), ...
        sum(P.phyStatus=="LOW_SNR_UNIT_CWER_ASSUMPTION"), ...
        'VariableNames',{'environmentLoss_dB','generated','received','lost','phyLost','hoLost', ...
        'loss_pct','onTime_pct','maxLossRun','curvePackets','highApproxPackets','lowApproxPackets'});
end
summary=vertcat(rows{:});
assert(summary.phyLost(1)==0 && summary.received(end)==0);
fprintf('PASS full slider sweep: 0:0.5:20 dB, all finite, exclusive loss accounting, paired monotonic losses.\n');
end
