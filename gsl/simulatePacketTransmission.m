function P = simulatePacketTransmission(L,CFG)
% One continuous simulated UDP session (no OS sockets, queue or retries).
validateattributes(CFG.duration_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetRate_pps,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetSize_bytes,{'numeric'},{'scalar','positive','integer'});
validateattributes(CFG.linkDataRate_bps,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.handoverInterruption_s,{'numeric'},{'scalar','nonnegative','finite'});
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
t=t(t<CFG.duration_s); n=numel(t); ix=discretize(t,L.time_s);
assert(all(isfinite(ix)),'GSL:PacketTime');
id=L.servingSatID(ix); outage=id==0;
snr=L.snr_dB(ix); elev=L.elevation_deg(ix);
interrupted=false(n,1); event=false(n,1);
for ht=L.time_s(logical(L.handoverEvent)).'
    % Tolerance only removes machine-roundoff at the half-open interval endpoints.
    tol=16*eps(max(1,abs(ht+CFG.handoverInterruption_s)));
    interrupted=interrupted | (t>=ht-tol & t<ht+CFG.handoverInterruption_s-tol);
    first=find(t>=ht-tol,1); if ~isempty(first), event(first)=true; end
end
hoLoss=~outage & interrupted;
attempted=~outage & ~hoLoss; % reaches PHY only after outage/HO priorities
per=nan(n,1); ebNo=per; cw=per; phyStatus=repmat("NOT_EVALUATED",n,1);
if any(attempted)
    [per(attempted),ebNo(attempted),cw(attempted),phyStatus(attempted)] = getPERfromSNR(snr(attempted),CFG);
end
known=attempted & isfinite(per); pending=attempted & ~known;
rx=zeros(n,1); phyLoss=zeros(n,1); rx(pending)=NaN; phyLoss(pending)=NaN;
stream=RandStream('mt19937ar','Seed',CFG.packetRandomSeed);
phyLoss(known)=double(rand(stream,sum(known),1)<per(known));
rx(known)=1-phyLoss(known);
lost=double(outage)+double(hoLoss)+phyLoss;
cause=repmat("UNRESOLVED_PHY",n,1);
cause(outage)="OUTAGE_LOSS"; cause(hoLoss)="HANDOVER_LOSS";
cause(known & phyLoss==1)="PHY_LOSS"; cause(known & rx==1)="SUCCESS";
P=table((1:n).',t,id,true(n,1),rx,lost,cause,elev,snr,ebNo,cw,per,interrupted, ...
    'VariableNames',{'packetID','time_s','servingSatID','generated','received','lost', ...
    'lossCause','servingElevation_deg','snr_dB','ebNo_dB','codewordErrorRate','phyPER','handoverInterruption'});
P.phyStatus=phyStatus; P.phy_loss=phyLoss; P.handover_loss=hoLoss; P.outage_loss=outage;
P.outcome_pending=pending; P.attempted=attempted; P.transmitted=attempted;
P.not_transmitted=~attempted; P.link_loss=phyLoss; % compatibility: PHY only
P.packet_id=P.packetID; P.serving_sat_id=P.servingSatID; P.per=P.phyPER;
P.propagation_delay_ms=L.propagationDelay_ms(ix);
P.transmission_delay_ms=repmat(1000*CFG.packetSize_bytes*8/CFG.linkDataRate_bps,n,1);
P.packet_interval_s=repmat(1/CFG.packetRate_pps,n,1);
P.handover_event=event; P.handover_state=P.handoverInterruption;
% Every packet has exactly one cause. Unknown PHY is never relabeled SUCCESS.
end
