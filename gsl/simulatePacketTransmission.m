function P = simulatePacketTransmission(L,CFG)
% One continuous simulated UDP session (no OS sockets, queue or retries).
validateattributes(CFG.duration_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetRate_pps,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetSize_bytes,{'numeric'},{'scalar','positive','integer'});
validateattributes(CFG.linkDataRate_bps,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.handoverInterruption_s,{'numeric'},{'scalar','nonnegative','finite'});
validateattributes(CFG.gslDeadline_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.receiverProcessing_s,{'numeric'},{'scalar','nonnegative','finite'});
assert(CFG.packetSize_bytes*8/CFG.linkDataRate_bps<=1/CFG.packetRate_pps, ...
    'GSL:QueueRequired','Serialization exceeds packet interval; queue model required.');
required={'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','elevation_deg','propagationDelay_ms'};
assert(all(ismember(required,L.Properties.VariableNames)),'GSL:LinkColumns');
assert(all(isfinite(L.time_s)) && all(diff(L.time_s)>0) && L.time_s(1)==0 ...
    && L.time_s(end)>=CFG.duration_s,'GSL:LinkTime');
assert(all(isfinite(L.servingSatID) & L.servingSatID>=0 & mod(L.servingSatID,1)==0));
assert(all(ismember(L.isLinkAvailable,[0 1])) && all(ismember(L.handoverEvent,[0 1])));
assert(all(logical(L.isLinkAvailable)==(L.servingSatID>0)),'GSL:LinkAvailability');
t=(0:ceil(CFG.duration_s*CFG.packetRate_pps)-1).'/CFG.packetRate_pps;
t=t(t<CFG.duration_s);
ids=(1:numel(t)).';
stream=RandStream('mt19937ar','Seed',CFG.packetRandomSeed);
% Pair the random draw by original packet ID across different policies.
P=evaluateGSLPackets(L,CFG,t,ids,rand(stream,numel(t),1));
end
