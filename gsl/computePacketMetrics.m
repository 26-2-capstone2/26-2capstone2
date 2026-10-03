function M=computePacketMetrics(P,window_s)
% Session denominator: GENERATED. Unknown PHY outcomes propagate to N/A.
validateattributes(window_s,{'numeric'},{'scalar','positive','finite'});
t=P.time_s; assert(~isempty(t) && all(diff(t)>0));
g=double(P.generated); tx=double(P.attempted); pending=double(P.outcome_pending);
rx=P.received; rx(isnan(rx))=0;
phy=P.phy_loss; phy(isnan(phy))=0;
ho=double(P.handover_loss); out=double(P.outage_loss); resolved=phy+ho+out;
assert(all(rx+resolved+pending==g) && all(rx+phy+pending==tx), 'GSL:PacketAccounting');
assert(all((rx>0)+(phy>0)+(ho>0)+(out>0)+(pending>0)==1),'GSL:ExclusiveCause');
M.generatedPackets=sum(g); M.attemptedPackets=sum(tx); M.transmittedPackets=sum(tx);
M.notTransmittedPackets=sum(ho+out); M.pendingPackets=sum(pending);
M.receivedPackets=sum(P.received); M.lostPackets=sum(P.lost);
M.phyLossPackets=sum(P.phy_loss); M.handoverLossPackets=sum(ho); M.outageLossPackets=sum(out);
M.linkLossPackets=M.phyLossPackets;
M.resolvedReceivedPackets=sum(rx); M.resolvedLostPackets=sum(resolved);
M.packetLossRatio=100*M.lostPackets/M.generatedPackets;
M.confirmedLossLowerBound_pct=100*M.resolvedLostPackets/M.generatedPackets;
M.packetDeliveryRatio=100*M.receivedPackets/M.generatedPackets;
M.generatedToReceivedRatio=M.packetDeliveryRatio; M.averageSuccessRate_pct=M.packetDeliveryRatio;
M.cumulativeGenerated=cumsum(g); M.cumulativeReceived=cumsum(P.received); M.cumulativeLost=cumsum(P.lost);
M.cumulativeKnownLoss=cumsum(resolved); M.cumulativePending=cumsum(pending);
M.cumulativeOutageLoss=cumsum(out); M.cumulativeHandoverLoss=cumsum(ho);
M.cumulativePhyLoss=cumsum(P.phy_loss); M.cumulativeLinkLoss=M.cumulativePhyLoss;
M.cumulativeAttempted=cumsum(tx); M.cumulativeTransmitted=M.cumulativeAttempted;
values=[g,rx,resolved,phy,ho,out,pending,tx]; prefix=[zeros(1,8);cumsum(values,1)];
rolling=zeros(height(P),8); left=1;
for right=1:height(P)
    tol=16*eps(max(1,abs(t(right))));
    while left<=right && t(left)<=t(right)-window_s+tol, left=left+1; end
    rolling(right,:)=prefix(right+1,:)-prefix(left,:);
end
M.rollingGeneratedPackets=rolling(:,1); M.rollingReceivedPackets=rolling(:,2);
M.rollingPhyLossPackets=rolling(:,4); M.rollingHandoverLossPackets=rolling(:,5);
M.rollingOutageLossPackets=rolling(:,6); M.rollingPendingPackets=rolling(:,7);
M.rollingTransmittedPackets=rolling(:,8); M.rollingLinkLossPackets=M.rollingPhyLossPackets;
ok=rolling(:,7)==0; M.rollingPacketLossRatio=nan(height(P),1); M.rollingSuccessRatio=M.rollingPacketLossRatio;
M.rollingPacketLossRatio(ok)=100*rolling(ok,3)./rolling(ok,1);
M.rollingSuccessRatio(ok)=100*rolling(ok,2)./rolling(ok,1);
M.rollingConfirmedLossLowerBound_pct=100*rolling(:,3)./rolling(:,1);
M.rollingFailureRatio=M.rollingPacketLossRatio;
interval=P.packet_interval_s(1); exposure=min(window_s,t-t(1)+interval);
M.rollingReceivedPacketsPerSecond=nan(height(P),1);
M.rollingReceivedPacketsPerSecond(ok)=rolling(ok,2)./exposure(ok);
M.averageReceivedPacketsPerSecond=M.receivedPackets/(t(end)-t(1)+interval);
M.window_s=window_s;
end
