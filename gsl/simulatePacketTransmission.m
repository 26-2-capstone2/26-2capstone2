function P = simulatePacketTransmission(L,CFG)
% Discrete-event SIMULATION, not OS UDP sockets or measured packet captures.
% Channel state is held on [sample_k, sample_k+1). No queue/retry/HO penalty.
validateattributes(CFG.duration_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetRate_pps,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.packetSize_bytes,{'numeric'},{'scalar','positive','integer'});
validateattributes(CFG.linkDataRate_bps,{'numeric'},{'scalar','positive','finite'});
assert(CFG.packetSize_bytes*8/CFG.linkDataRate_bps <= 1/CFG.packetRate_pps, ...
    'GSL:QueueRequired','Serialization exceeds the packet interval; queue model required.');
required = {'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','propagationDelay_ms'};
assert(all(ismember(required,L.Properties.VariableNames)),'GSL:LinkColumns','Missing link-state columns.');
assert(all(isfinite(L.time_s)) && all(diff(L.time_s)>0) && ...
    L.time_s(1)==0 && L.time_s(end)>=CFG.duration_s,'GSL:LinkTime','Link state must cover [0,duration].');
assert(all(isfinite(L.servingSatID) & L.servingSatID>=0 & mod(L.servingSatID,1)==0));
assert(all(ismember(L.isLinkAvailable,[0 1])) && all(ismember(L.handoverEvent,[0 1])));
t = (0:ceil(CFG.duration_s*CFG.packetRate_pps)-1).'/CFG.packetRate_pps;
t = t(t<CFG.duration_s); % half-open [0,T): duration*rate packets when the product is an integer
n = numel(t); stateIndex = discretize(t,L.time_s);
assert(all(isfinite(stateIndex)),'GSL:PacketTime','Packet outside channel time grid.');
id = L.servingSatID(stateIndex);
tx = id>0 & logical(L.isLinkAvailable(stateIndex));
snr = L.snr_dB(stateIndex); delay = L.propagationDelay_ms(stateIndex);
per = nan(n,1); rx = zeros(n,1); lost = zeros(n,1);
rx(tx) = NaN; lost(tx) = NaN; % untransmitted != PER loss; unresolved != success
if any(tx)
    if isempty(CFG.perModel)
        estimate=getPERfromSNR(snr(tx),CFG.packetSize_bytes,CFG.referenceNoiseBandwidth_Hz,CFG.linkDataRate_bps);
    else
        estimate=CFG.perModel(snr(tx));
    end
    assert(isnumeric(estimate) && isreal(estimate) && numel(estimate)==sum(tx), ...
        'GSL:PERShape','PER model must return one real probability per transmitted packet.');
    estimate = estimate(:);
    assert(all(isnan(estimate) | (isfinite(estimate) & estimate>=0 & estimate<=1)), ...
        'GSL:InvalidPER','PER must be NaN (unknown) or in [0,1].');
    if any(isfinite(estimate))
        assert(strlength(string(CFG.perModelSource))>0,'GSL:MissingPERSource', ...
            'Document the PER curve/source and applicable SNR definition in CFG.perModelSource.');
    end
    per(tx) = estimate;
    assert(~any(isfinite(per) & ~isfinite(snr)),'GSL:MissingSNR','Known PER requires finite SNR.');
    known = tx & isfinite(per);
    stream = RandStream('mt19937ar','Seed',CFG.packetRandomSeed);
    lost(known) = double(rand(stream,sum(known),1)<per(known));
    rx(known) = 1-lost(known);
end
handoverState = logical(L.handoverEvent(stateIndex));
handoverEvent = false(n,1);
% Mark at most one packet at/after each event; plots use exact link event times.
for ht = L.time_s(L.handoverEvent).'
    first = find(t>=ht,1); if ~isempty(first), handoverEvent(first)=true; end
end
P = table((1:n).',t,id,true(n,1),tx,rx,lost,snr,per,delay, ...
    handoverEvent,handoverState,repmat(1000*CFG.packetSize_bytes*8/CFG.linkDataRate_bps,n,1), ...
    tx & isnan(per),~tx,'VariableNames',{'packet_id','time_s','serving_sat_id', ...
    'generated','transmitted','received','lost','snr_dB','per','propagation_delay_ms', ...
    'handover_event','handover_state','transmission_delay_ms','outcome_pending','not_transmitted'});
P.attempted=P.transmitted;
P.link_loss=P.lost;
P.outage_loss=~tx;
P.lost=P.link_loss+double(P.outage_loss);
P.packet_interval_s=repmat(1/CFG.packetRate_pps,n,1);
% generated = received + lost + pending; total lost = outage + link loss.
% Eventual outcomes attributed to generation/send time, not arrival time.
end
