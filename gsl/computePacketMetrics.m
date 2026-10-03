function M=computePacketMetrics(P,window_s)
% Failure denominator is generated; lost includes outage and link losses.
validateattributes(window_s,{'numeric'},{'scalar','positive','finite'});
t=P.time_s; assert(all(diff(t)>0) && ~isempty(t));
tx=double(P.transmitted); pending=double(P.outcome_pending);
rx=P.received; rx(isnan(rx))=0;
ll=P.link_loss; ll(isnan(ll))=0;
ol=double(P.outage_loss); total=ol+ll;
assert(all(rx+ll+pending==tx) && all(tx+ol==double(P.generated)), ...
    'GSL:PacketAccounting','Packet accounting failed.');
M.generatedPackets=sum(P.generated); M.attemptedPackets=sum(tx);
M.transmittedPackets=M.attemptedPackets; % compatibility alias
M.notTransmittedPackets=sum(ol); M.outageLossPackets=sum(ol);
M.linkLossPackets=sum(P.link_loss); M.pendingPackets=sum(pending);
M.resolvedReceivedPackets=sum(rx); M.resolvedLostPackets=sum(total);
M.receivedPackets=sum(P.received); M.lostPackets=sum(P.lost);
M.packetLossRatio=ratio(M.lostPackets,M.generatedPackets);
M.packetDeliveryRatio=ratio(M.receivedPackets,M.generatedPackets);
M.generatedToReceivedRatio=M.packetDeliveryRatio;
M.attemptedLinkLossRatio=ratio(M.linkLossPackets,M.attemptedPackets);
M.averageSuccessRate_pct=M.packetDeliveryRatio;
M.cumulativeGenerated=cumsum(double(P.generated));
M.cumulativeTransmitted=cumsum(tx); M.cumulativeAttempted=M.cumulativeTransmitted;
M.cumulativeReceived=cumsum(P.received); M.cumulativeLost=cumsum(P.lost);
M.cumulativeOutageLoss=cumsum(ol); M.cumulativeLinkLoss=cumsum(P.link_loss);
% Prefix sums + sliding left edge implement the actual (t-window,t] window.
values=[double(P.generated),tx,rx,total,ol,ll,pending];
prefix=[zeros(1,7);cumsum(values,1)]; rolling=zeros(height(P),7); left=1;
for right=1:height(P)
    tol=16*eps(max(1,abs(t(right))));
    while left<=right && t(left)<=t(right)-window_s+tol, left=left+1; end
    rolling(right,:)=prefix(right+1,:)-prefix(left,:);
end
M.rollingGeneratedPackets=rolling(:,1); M.rollingTransmittedPackets=rolling(:,2);
M.rollingReceivedPackets=rolling(:,3);
M.rollingOutageLossPackets=rolling(:,5); M.rollingLinkLossPackets=rolling(:,6);
M.rollingPendingPackets=rolling(:,7);
M.rollingPacketLossRatio=nan(height(P),1);
M.rollingSuccessRatio=nan(height(P),1);
ok=rolling(:,1)>0 & rolling(:,7)==0;
M.rollingPacketLossRatio(ok)=100*rolling(ok,4)./rolling(ok,1);
M.rollingFailureRatio=M.rollingPacketLossRatio;
M.rollingSuccessRatio(ok)=100*rolling(ok,3)./rolling(ok,1);
if height(P)>1, interval=median(diff(t)); else, interval=P.packet_interval_s(1); end
exposure=min(window_s,t-t(1)+interval); % partial startup window, not five seconds of invented history
M.rollingReceivedPacketsPerSecond=nan(height(P),1);
M.rollingReceivedPacketsPerSecond(ok)=rolling(ok,3)./exposure(ok);
M.averageReceivedPacketsPerSecond=M.receivedPackets/(t(end)-t(1)+interval);
M.window_s=window_s;
end
function r=ratio(n,d)
if d==0, r=NaN; else, r=100*n/d; end
end
