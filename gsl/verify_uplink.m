function verify_uplink()
% Focused accounting/timing/channel tests; no satellite toolbox needed here.
C=configGSL(); C.duration_s=2; C.handoverInterruption_s=.1;
C.channelScenario='clear'; C.channelSigma_dB=0;
L=table((0:2).',[1;2;2],true(3,1),[false;true;false], ...
    10*ones(3,1),45*ones(3,1),3*ones(3,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','elevation_deg','propagationDelay_ms'});
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,1);
assert(height(P)==120 && M.handoverLossPackets==6 && M.lostPackets==6);
assert(M.maxConsecutiveLoss==6 && M.lossRunCount==1 && M.lossRuns.firstPacketID==61);
assert(M.lossRuns.lastPacketID==66 && all(P.onTime(P.received==1)));
noHo=L; noHo.handoverEvent(:)=false; paired=simulatePacketTransmission(noHo,C);
assert(isequal(P.phyRandomDraw,paired.phyRandomDraw),'PHY draws must remain paired by original ID');
assert(abs(M.packetLossRatio-5)<1e-10 && M.onTimeDeliveryRate_pct==95);
assert(all(abs(M.rollingOnTimeDeliveryRate_pct+M.rollingDeadlineFailureRate_pct-100)<1e-9));
% A late delivered packet is not an undelivered packet.
C.gslDeadline_s=.001;
Q=simulatePacketTransmission(L,C); N=computePacketMetrics(Q,1);
assert(N.latePackets==114 && N.lostPackets==6 && N.deadlineFailureRate_pct==100);
assert(all(N.rollingOnTimeDeliveryRate_pct==0));
assert(all(abs(N.rollingDeadlineFailureRate_pct-100)<1e-9));
assert(any(N.rollingLateRate_pct>0));
% Last arrival can follow generation stop; it must still be observed.
C.receiverProcessing_s=.1;
Q=simulatePacketTransmission(L,C); N=computePacketMetrics(Q,1);
assert(N.observationEnd_s>C.duration_s && N.receivedPackets+N.lostPackets==120);
% All lost, no lost, and unresolved cases do not fabricate burst counts.
Q=P; Q.lost(:)=0; Q.received(:)=1; Q.phy_loss(:)=0; Q.handover_loss(:)=0;
Q.attempted(:)=1; Q.onTime(:)=true; Q.late(:)=false;
N=computePacketMetrics(Q,1); assert(N.maxConsecutiveLoss==0 && isempty(N.lossRuns));
Q.received(:)=0; Q.lost(:)=1; Q.phy_loss(:)=1; Q.onTime(:)=false;
N=computePacketMetrics(Q,1); assert(N.maxConsecutiveLoss==120 && N.lossRunCount==1);
[p,~,cw,status]=getPERfromSNR([-10;1;20],C);
assert(p(1)==1 && p(3)>0 && p(3)<1e-5 && cw(3)>0 && all(isfinite(p)));
assert(status(3)=="HIGH_SNR_ENDPOINT_BOUND_ASSUMPTION");
C.duration_s=600; C.channelScenario='synthetic_fade'; C.channelSigma_dB=.7;
A=gslChannel(C); B=gslChannel(C); assert(isequal(A,B));
assert(max(A.testFadeLoss_dB)>9.9);
fprintf('PASS verify_uplink: half-open handover, original-ID runs, deadline separation, final-arrival flush, curve bounds, reproducible channel.\n');
end
