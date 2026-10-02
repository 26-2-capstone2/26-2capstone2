function verify_packet_integration()
% Full real geometry integration, production PER placeholder only.
verify_packets();
C=configGSL(); C.openViewer=false;
timer=tic; R=main_gsl_simulation(C); L=R.linkState; P=R.packetTable; M=R.packetMetrics;
assert(M.generatedPackets==12000 && M.transmittedPackets<=M.generatedPackets);
assert(M.resolvedReceivedPackets+M.resolvedLostPackets+M.pendingPackets==M.transmittedPackets);
assert(M.pendingPackets==M.transmittedPackets && isnan(M.packetLossRatio));
assert(isequal(R.geometry.isVisible,R.geometry.accessStatus));
assert(isequal(size(R.geometry.elevation_deg),[601 1584]));
valid=L.servingSatID>0;
assert(all(L.elevation_deg(valid)>=C.minElevation_deg));
assert(all(L.propagationDelay_ms(valid)>0 & isfinite(L.snr_dB(valid))));
assert(all(L.residualDoppler_Hz(valid)==0));
assert(all(abs(L.rawDoppler_Hz(valid) + L.radialVelocity_mps(valid)/299792458*C.carrierFrequency_Hz)<1e-6));
% Independent range-rate difference check away from serving changes.
same=false(height(L),1);
same(2:end-1)=L.servingSatID(1:end-2)==L.servingSatID(2:end-1) & ...
    L.servingSatID(3:end)==L.servingSatID(2:end-1) & valid(2:end-1);
dr=gradient(L.slantRange_m,C.channelUpdateStep_s);
assert(max(abs(dr(same)-L.radialVelocity_mps(same)))<1);
% Compare PSD form with the equivalent total-EIRP formula at a TEST bandwidth.
B_Hz=20e6; % algebraic unit check, not a new scenario bandwidth assumption
eirp=C.txEIRPDensity_dBW_per_MHz+10*log10(B_Hz/1e6);
equivalent=eirp+C.rxGT_dB_per_K-L.fspl_dB-10*log10(1.380649e-23)-10*log10(B_Hz);
assert(max(abs(equivalent(valid)-L.snr_dB(valid)))<1e-10);
csv=readtable(fullfile(C.outputDir,'packet_results.csv'));
assert(height(csv)==12000 && all(isnan(csv.received(csv.transmitted==1))));
assert(all(csv.generated==1) && sum(csv.transmitted)==M.transmittedPackets);
saved=load(fullfile(C.outputDir,'packet_results.mat'));
assert(isequaln(saved.P.received,P.received));
fprintf('PASS: full geometry integration, CSV/MAT roundtrip, range-rate/Doppler and SNR units.\n');
fprintf('Full run %.1f s; handovers=%d; SNR range=[%.3f, %.3f] dB; delay=[%.3f, %.3f] ms.\n', ...
    toc(timer),sum(L.handoverEvent),min(L.snr_dB),max(L.snr_dB), ...
    min(L.propagationDelay_ms),max(L.propagationDelay_ms));
end
