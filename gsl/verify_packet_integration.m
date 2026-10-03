function verify_packet_integration()
% Full numeric/CSV/MAT integration with the current default reference model.
verify_packets;
C=configGSL(); C.openViewer=false; R=main_gsl_simulation(C);
L=R.linkState; P=R.packetTable; M=R.packetMetrics;
assert(M.generatedPackets==36000 && M.attemptedPackets<=M.generatedPackets);
assert(M.resolvedReceivedPackets+M.resolvedLostPackets+M.pendingPackets==M.generatedPackets);
assert(isequal(R.geometry.isVisible,R.geometry.accessStatus));
valid=L.servingSatID>0;
assert(all(L.elevation_deg(valid)>=C.minElevation_deg));
assert(all(L.propagationDelay_ms(valid)>0 & isfinite(L.snr_dB(valid))));
assert(all(L.residualDoppler_Hz(valid)==0));
assert(all(abs(L.rawDoppler_Hz(valid)+L.radialVelocity_mps(valid)/299792458*C.carrierFrequency_Hz)<1e-6));
same=false(height(L),1);
same(2:end-1)=L.servingSatID(1:end-2)==L.servingSatID(2:end-1) & ...
    L.servingSatID(3:end)==L.servingSatID(2:end-1) & valid(2:end-1);
dr=gradient(L.slantRange_m,C.channelUpdateStep_s);
assert(max(abs(dr(same)-L.radialVelocity_mps(same)))<1);
B_Hz=20e6; eirp=C.txEIRPDensity_dBW_per_MHz+10*log10(B_Hz/1e6);
equivalent=eirp+C.rxGT_dB_per_K-L.fspl_dB-10*log10(1.380649e-23)-10*log10(B_Hz);
assert(max(abs(equivalent(valid)-L.snr_dB(valid)))<1e-10);
csv=readtable(fullfile(C.outputDir,'packet_results.csv'));
assert(height(csv)==36000 && sum(csv.attempted)==M.attemptedPackets);
saved=load(fullfile(C.outputDir,'packet_results.mat'));
assert(isequaln(saved.P.lost,P.lost) && isequaln(saved.M,R.packetMetrics));
assert(isnan(M.lostPackets) && isnan(M.receivedPackets) && isnan(M.phyLossPackets));
assert(M.handoverLossPackets==60 && M.outageLossPackets==0 && M.pendingPackets==35940);
assert(M.confirmedLossLowerBound_pct==100*60/36000);
assert(all(P.lossCause(P.handover_loss)=="HANDOVER_LOSS"));
assert(isequal(P.packetID,(1:36000).'));
fprintf('PASS: full geometry, CSV/MAT roundtrip, accounting, range-rate/Doppler and SNR units.\n');
end
