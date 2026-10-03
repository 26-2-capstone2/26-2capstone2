function verify_packets()
% SOFTWARE fixtures below test accounting; they are not measured GSL results.
C=configGSL(); C.makePlots=false; C.openViewer=false; C.exportResults=false;
L=fixture((0:600).'); L.snr_dB(:)=25;
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(height(P)==36000 && M.generatedPackets==36000 && M.attemptedPackets==36000);
assert(M.receivedPackets==36000 && M.lostPackets==0 && M.packetLossRatio==0);
assert(all(M.rollingGeneratedPackets(P.time_s>=5)==300));
assert(max(abs(M.rollingReceivedPacketsPerSecond-60))<1e-8);
assert(all(abs(P.transmission_delay_ms-.0256)<1e-12));
C.packetRate_pps=20; P=simulatePacketTransmission(L,C);
assert(height(P)==12000);
fprintf('PASS: 160 Bytes; 20/60 pps; 12000/36000 packets; rolling throughput/window.\n');
p=getPERfromSNR([0 5 10 20],160,50e6,50e6);
assert(all(diff(p)<0) && p(1)>.99 && p(3)>0 && p(3)<.01);
small=getPERfromSNR(10,1,50e6,50e6);
assert(abs(small-(1-(1-.5*erfc(sqrt(10)))^8))<1e-12);
assert(getPERfromSNR(5,160,100e6,50e6)<getPERfromSNR(5,160,50e6,50e6));
fprintf('PASS: BPSK BER/PER conversion, bandwidth conversion and size dependence.\n');
% Moderate-SNR reference fixture checks actual Bernoulli link failures.
C.duration_s=100; C.packetRate_pps=60; L=fixture((0:100).');
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.linkLossPackets>0 && M.receivedPackets>0 && M.outageLossPackets==0);
assert(M.packetLossRatio==100*M.linkLossPackets/M.generatedPackets);
fprintf('PASS: reference model at 10dB produces both success and link failure.\n');
C.duration_s=10; C.packetRate_pps=60; L=fixture((0:10).');
L.isLinkAvailable(L.time_s>=2 & L.time_s<4)=false; L.servingSatID(~L.isLinkAvailable)=0;
L.handoverEvent(L.time_s==5)=true; L.servingSatID(L.time_s>=5)=2;
C.perModel=@(s)zeros(size(s)); C.perModelSource='SOFTWARE TEST: success';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.generatedPackets==600 && M.attemptedPackets==480 && M.receivedPackets==480);
assert(M.outageLossPackets==120 && M.linkLossPackets==0 && M.lostPackets==120);
assert(M.packetLossRatio==20 && M.averageSuccessRate_pct==80);
assert(all(M.cumulativeReceived+M.cumulativeLost==M.cumulativeGenerated));
assert(all(P.link_loss(~P.attempted)==0 & P.lost(~P.attempted)==1));
assert(sum(P.handover_event)==1);
for k=1:height(P)
    inside=P.time_s>P.time_s(k)-5+1e-12 & P.time_s<=P.time_s(k);
    expected=100*sum(P.lost(inside))/sum(P.generated(inside));
    assert(abs(M.rollingFailureRatio(k)-expected)<1e-9);
end
C.perModel=@(s)ones(size(s)); C.perModelSource='SOFTWARE TEST: link failure';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.linkLossPackets==480 && M.outageLossPackets==120 && M.lostPackets==600);
assert(M.packetLossRatio==100 && M.averageSuccessRate_pct==0);
L.isLinkAvailable(:)=false; L.servingSatID(:)=0;
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.attemptedPackets==0 && M.lostPackets==600 && M.packetLossRatio==100);
assert(M.linkLossPackets==0 && isnan(M.attemptedLinkLossRatio));
fprintf('PASS: outage/link split; generated denominator; window oracle; all-outage.\n');
L=fixture((0:10).'); C.perModel=@(s)nan(size(s)); C.perModelSource='UNKNOWN PER';
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.pendingPackets==600 && isnan(M.lostPackets) && all(isnan(M.rollingFailureRatio)));
C.perModel=@(s)s*0; L.snr_dB(1:2)=NaN;
P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,5);
assert(M.pendingPackets==120);
assert(all(isnan(M.rollingFailureRatio(P.time_s<7-1/60))));
assert(all(M.rollingFailureRatio(P.time_s>=7-1/60)==0));
C.perModel=@(s).37*ones(size(s)); C.perModelSource='SOFTWARE TEST: RNG';
L.snr_dB(:)=10; before=rng; A=simulatePacketTransmission(L,C); B=simulatePacketTransmission(L,C);
assert(isequal(A.lost,B.lost) && isequal(before,rng));
C.perModel=@(s)2*ones(size(s)); expectError(@()simulatePacketTransmission(L,C),'GSL:InvalidPER');
C.perModel=@(s)zeros(size(s)); C.perModelSource='';
expectError(@()simulatePacketTransmission(L,C),'GSL:MissingPERSource');
fprintf('PASS: unknown outcomes stay N/A; window recovery; deterministic RNG; invalid PER.\n');
el=[50 48;50 54;50 55;24 26;0 0;30 31;32 32];
[id,ho]=selectServingSatellite(el,el>=25,4);
assert(isequal(id,[1;2;2;2;0;2;2]) && isequal(find(ho),2));
[id,ho]=selectServingSatellite([50 30;24 26],[true true;false true],4);
assert(isequal(id,[1;2]) && ho(2));
[id,~]=selectServingSatellite([50 50;50 50],true(2),0); assert(isequal(id,[1;1]));
fprintf('PASS: inclusive >=4 deg handover, forced switch, outage, reacquisition, ties.\n');
fprintf('ALL PACKET UNIT CHECKS PASSED.\n');
end
function L=fixture(t)
n=numel(t);
L=table(t,ones(n,1),true(n,1),false(n,1),10*ones(n,1),2*ones(n,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','snr_dB','propagationDelay_ms'});
end
function expectError(fn,id)
caught=false; try, fn(); catch e, assert(strcmp(e.identifier,id),e.message); caught=true; end
assert(caught);
end
