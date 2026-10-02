function M = computePacketMetrics(P,window_s)
% Rolling window (t-window_s,t], denominator = transmitted packets only.
validateattributes(window_s,{'numeric'},{'scalar','positive','finite'});
t = P.time_s; assert(all(diff(t)>0));
tx = double(P.transmitted); pending = double(P.outcome_pending);
rxKnown = P.received; rxKnown(isnan(rxKnown))=0;
lossKnown = P.lost; lossKnown(isnan(lossKnown))=0;
assert(all(rxKnown+lossKnown+pending==tx),'GSL:PacketAccounting','Packet accounting failed.');
M.generatedPackets = sum(P.generated); M.transmittedPackets = sum(tx);
M.notTransmittedPackets = sum(~P.transmitted); M.pendingPackets = sum(pending);
M.resolvedReceivedPackets = sum(rxKnown); M.resolvedLostPackets = sum(lossKnown);
M.receivedPackets = sum(P.received); M.lostPackets = sum(P.lost); % retain NaN
M.packetLossRatio = ratio(M.lostPackets,M.transmittedPackets);
M.packetDeliveryRatio = ratio(M.receivedPackets,M.transmittedPackets);
M.generatedToReceivedRatio = ratio(M.receivedPackets,M.generatedPackets);
M.cumulativeGenerated = cumsum(double(P.generated));
M.cumulativeTransmitted = cumsum(tx);
M.cumulativeReceived = cumsum(P.received); M.cumulativeLost = cumsum(P.lost);
n = height(P); rollingTx = zeros(n,1); rollingLoss = rollingTx; rollingPending = rollingTx;
ct = [0;cumsum(tx)]; cl = [0;cumsum(lossKnown)]; cp = [0;cumsum(pending)];
left = 1;
for right = 1:n
    % Epsilon tolerance only resolves floating-point equality at the left edge.
    tol = 16*eps(max(1,abs(t(right))));
    while left<=right && t(left)<=t(right)-window_s+tol, left=left+1; end
    rollingTx(right)=ct(right+1)-ct(left);
    rollingLoss(right)=cl(right+1)-cl(left);
    rollingPending(right)=cp(right+1)-cp(left);
end
M.rollingTransmittedPackets = rollingTx;
M.rollingPacketLossRatio = nan(n,1);
ok = rollingTx>0 & rollingPending==0;
M.rollingPacketLossRatio(ok)=100*rollingLoss(ok)./rollingTx(ok);
M.window_s = window_s;
end
function r = ratio(n,d)
if d==0, r=NaN; else, r=100*n/d; end
end
