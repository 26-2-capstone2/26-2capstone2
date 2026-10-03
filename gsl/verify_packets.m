function verify_packets()
% Source-curve numeric tests + deterministic software fixtures (not research data).
C=configGSL(); C.duration_s=4;
[p,e,cw,status]=getPERfromSNR([0;1;2],C);
assert(all(isnan(p)) && all(isnan(e)) && all(isnan(cw)) && all(status=="MISSING_BANDWIDTH_OR_INFORMATION_RATE"));
D=readtable(fullfile(fileparts(mfilename('fullpath')),'ar4ja_r12_k1024_cwer.csv'));
assert(height(D)==22 && D.ebNo_dB(1)==0 && all(diff(D.codewordErrorRate)<=0));
% Unit fixture ONLY: ratio 1 and a documented synthetic mapping. Never exported.
F=C; F.noiseBandwidth_Hz=50e6; F.informationBitRate_bps=50e6;
F.phyMappingSource='UNIT TEST ONLY: B/Rb=1; not a research bandwidth';
[p,e,cw]=getPERfromSNR(D.ebNo_dB,F);
assert(max(abs(cw-D.codewordErrorRate))<1e-12 && max(abs(e-D.ebNo_dB))<1e-12);
assert(max(abs(p-(1-(1-cw).^2)))<1e-12);
[~,e2,c2]=getPERfromSNR(4,setfield(F,'noiseBandwidth_Hz',25e6)); %#ok<SFLD>
assert(abs(e2-(4+10*log10(.5)))<1e-12 && isfinite(c2));
assert(all(isnan(getPERfromSNR([-1;3;24],F)))); % no endpoint clamping/extrapolation
bad=F; bad.phyMappingSource=''; failed=false;
try, getPERfromSNR(1,bad); catch ex, failed=strcmp(ex.identifier,'GSL:MissingPHYMappingSource'); end
assert(failed);
L=fixture([1;2;0;3;3],[false;true;false;false;false],[2;0;NaN;2;2]);
rng(123); before=rng; P=simulatePacketTransmission(L,F); after=rng; assert(isequal(before,after));
assert(isequal(P.packetID,(1:240).') && all(P.generated));
assert(sum(P.handover_loss)==6 && sum(P.outage_loss)==60 && sum(P.phy_loss)==54);
assert(all(P.lossCause(P.time_s>=1 & P.time_s<1.1)=="HANDOVER_LOSS"));
assert(P.lossCause(find(abs(P.time_s-1.1)<1e-12,1))=="PHY_LOSS");
M=computePacketMetrics(P,5);
assert(M.generatedPackets==240 && M.receivedPackets==120 && M.lostPackets==120);
assert(M.phyLossPackets==54 && M.handoverLossPackets==6 && M.outageLossPackets==60);
assert(M.packetLossRatio==50 && M.averageReceivedPacketsPerSecond==30);
% Outage has precedence even when an interruption overlaps that state.
O=L; O.handoverEvent(3)=true; PO=simulatePacketTransmission(O,F);
assert(all(PO.lossCause(PO.time_s>=2 & PO.time_s<2.1)=="OUTAGE_LOSS"));
assert(sum(PO.handover_loss)==6);
% Exact interval tests across a late floating-point endpoint and different rates.
T=C; T.duration_s=600; T.packetRate_pps=60;
H=fixture([1;2;2],[false;true;false],[2;2;2]); H.time_s=[0;359;600];
PH=simulatePacketTransmission(H,T);
assert(sum(PH.handover_loss)==6 && ~PH.handover_loss(find(abs(PH.time_s-359.1)<1e-12,1)));
T.packetRate_pps=33; PH=simulatePacketTransmission(H,T); assert(sum(PH.handover_loss)==4);
T.handoverInterruption_s=0; PH=simulatePacketTransmission(H,T); assert(~any(PH.handover_loss));
% Unknown PHY accounting does not silently become success or zero loss.
PU=simulatePacketTransmission(L,C); MU=computePacketMetrics(PU,1);
assert(MU.pendingPackets==174 && MU.resolvedLostPackets==66 && isnan(MU.lostPackets));
assert(isnan(MU.receivedPackets) && isnan(MU.phyLossPackets) && isnan(MU.packetLossRatio));
assert(all(isnan(PU.received(PU.outcome_pending))));
assert(all(PU.lossCause(PU.outcome_pending)=="UNRESOLVED_PHY"));
% Rolling window oracle: (t-1,t], generated denominator; unresolved windows N/A.
Q=computePacketMetrics(P,1);
for k=1:height(P)
    ix=P.time_s>P.time_s(k)-1+16*eps(max(1,abs(P.time_s(k)))) & P.time_s<=P.time_s(k);
    assert(abs(Q.rollingPacketLossRatio(k)-100*sum(P.lost(ix))/sum(P.generated(ix)))<1e-10);
end
assert(isfinite(MU.rollingPacketLossRatio(find(abs(PU.time_s-2.983333333333333)<1e-10,1))));
% Strict 4-degree hysteresis: equality retains, greater switches.
E=[40 39;40 44;40 44.01;24 45;24 24;30 29]; V=E>=25;
[id,ho]=selectServingSatellite(E,V,4);
assert(isequal(id,[1;1;2;2;0;1]) && isequal(ho,[false;false;true;false;false;false]));
assert(all(id(any(V,2))>0));
fprintf('PASS: actual JPL lookup; B/Rb units; no extrapolation; 2-codeword PER.\n');
fprintf('PASS: continuous IDs; exclusive PHY/HO/outage causes; strict hysteresis; 100ms half-open boundaries.\n');
fprintf('PASS: RNG isolation; rolling window oracle; unknown PHY stays N/A.\n');
end
function L=fixture(ids,ho,snr)
n=numel(ids); L=table((0:n-1).',ids,ids>0,ho,snr,repmat(50,n,1),repmat(2,n,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','elevation_deg','propagationDelay_ms'});
end
