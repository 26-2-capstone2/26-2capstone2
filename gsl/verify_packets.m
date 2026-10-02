function verify_packets()
% Deterministic SOFTWARE TEST FIXTURES below are NOT research PER curves.
C=configGSL(); C.makePlots=false; C.openViewer=false; C.exportResults=false;
L=fixture((0:600).');
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(height(P)==12000 && P.time_s(end)==599.95 && all(diff(P.packet_id)==1));
assert(M.generatedPackets==12000 && M.transmittedPackets==12000);
assert(M.pendingPackets==12000 && isnan(M.receivedPackets) && isnan(M.lostPackets));
assert(all(isnan(M.rollingPacketLossRatio)));
assert(all(M.rollingTransmittedPackets(P.time_s>=5)==100));
C.packetRate_pps=60; P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(height(P)==36000 && all(M.rollingTransmittedPackets(P.time_s>=5)==300));
fprintf('PASS: 20/60 pps -> 12000/36000 packets; 5s windows -> 100/300; unknown PER stays unknown.\n');

C.duration_s=10; C.packetRate_pps=20; L=fixture((0:10).');
L.isLinkAvailable(L.time_s>=2 & L.time_s<4)=false;
L.servingSatID(L.time_s>=2 & L.time_s<3)=0;
C.perModel=@(snr) zeros(size(snr)); C.perModelSource='SOFTWARE TEST ONLY: all success';
L.handoverEvent(L.time_s==5)=true; L.servingSatID(L.time_s>=5)=2;
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.generatedPackets==200 && M.transmittedPackets==160 && M.notTransmittedPackets==40);
assert(M.receivedPackets==160 && M.lostPackets==0 && M.packetLossRatio==0);
assert(M.packetDeliveryRatio==100 && M.generatedToReceivedRatio==80);
assert(sum(P.handover_event)==1 && sum(P.handover_state)==20);
assert(P.handover_event(P.time_s==5) && all(P.serving_sat_id(P.time_s>=5)==2));
assert(all(P.received(~P.transmitted)==0 & P.lost(~P.transmitted)==0));
assert(all(P.transmission_delay_ms==0.024));
assert(all(M.cumulativeReceived+M.cumulativeLost==M.cumulativeTransmitted));

C.perModel=@(snr) ones(size(snr)); C.perModelSource='SOFTWARE TEST ONLY: all loss';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.receivedPackets==0 && M.lostPackets==160 && M.packetLossRatio==100);
assert(all(M.rollingPacketLossRatio(M.rollingTransmittedPackets>0)==100));
L.isLinkAvailable(:)=false; P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.transmittedPackets==0 && M.receivedPackets==0 && M.lostPackets==0);
assert(isnan(M.packetLossRatio) && isnan(M.packetDeliveryRatio));
fprintf('PASS: outage vs loss, zero transmissions, all-success/all-loss accounting, one handover marker.\n');

% Time-window oracle with nonuniform link outcomes; no realistic channel claim.
L=fixture((0:10).'); L.snr_dB=mod(L.time_s,2);
C.perModel=@(snr) snr; C.perModelSource='SOFTWARE TEST ONLY: alternating 0/1';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,1.25);
for k=1:height(P)
    inside=P.time_s>P.time_s(k)-1.25+1e-12 & P.time_s<=P.time_s(k);
    expected=100*sum(P.lost(inside))/sum(P.transmitted(inside));
    assert(abs(M.rollingPacketLossRatio(k)-expected)<1e-9);
end
assert(max(M.rollingPacketLossRatio)>min(M.rollingPacketLossRatio), ...
    'Rolling result is not a global constant.');
C.perModel=@(snr) 0.37*ones(size(snr)); C.perModelSource='SOFTWARE TEST ONLY: RNG';
before=rng; P1=simulatePacketTransmission(L,C); P2=simulatePacketTransmission(L,C);
assert(isequal(P1.lost,P2.lost) && isequal(before,rng));
C.perModel=@(snr) 2*ones(size(snr)); expectError(@()simulatePacketTransmission(L,C),'GSL:InvalidPER');
C.perModel=@(snr) zeros(size(snr)); C.perModelSource='';
expectError(@()simulatePacketTransmission(L,C),'GSL:MissingPERSource');
fprintf('PASS: true moving-window oracle, deterministic private RNG, invalid PER rejection.\n');

L=fixture((0:10).'); L.snr_dB(1:2)=NaN;
C.perModel=@(snr) snr*0; C.perModelSource='SOFTWARE TEST ONLY: partial unknown';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.pendingPackets==40 && isnan(M.receivedPackets));
assert(all(isnan(M.rollingPacketLossRatio(P.time_s<6.95))));
assert(all(M.rollingPacketLossRatio(P.time_s>=6.95)==0));
fprintf('PASS: unresolved outcomes expire from the rolling window without becoming false zero loss.\n');

el=[50 48;50 54;50 55;24 26;0 0;30 31;32 32];
[id,ho]=selectServingSatellite(el,el>=25,4);
assert(isequal(id,[1;1;2;2;0;2;2]) && isequal(find(ho),3));
[id,ho]=selectServingSatellite([50 30;24 26],[true true;false true],4);
assert(isequal(id,[1;2]) && ho(2));
fprintf('PASS: strict >4-degree hysteresis, forced switch, outage and reacquisition.\n');
fprintf('ALL PACKET UNIT CHECKS PASSED. Synthetic test probabilities were not exported as research results.\n');
end
function L=fixture(t)
n=numel(t);
L=table(t,ones(n,1),true(n,1),false(n,1),10*ones(n,1),2*ones(n,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','propagationDelay_ms'});
end
function expectError(fn,id)
caught=false;
try, fn(); catch e, assert(strcmp(e.identifier,id),e.message); caught=true; end
assert(caught,'Expected error was not raised.');
end
