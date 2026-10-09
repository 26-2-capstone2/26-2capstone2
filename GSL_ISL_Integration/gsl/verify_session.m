function verify_session()
% Current end-to-end validation; no shell quoting or synthetic research output.
verify_packet_integration;
verify_visualization;
C=configGSL(); C.openViewer=false;
C.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_packets_stress');
R=main_gsl_simulation(C);
assert(R.packetMetrics.generatedPackets==36000 && R.packetMetrics.handoverLossPackets==60);
assert(R.packetMetrics.pendingPackets==35940 && isnan(R.packetMetrics.packetLossRatio));
fprintf('PASS: current baseline and additional result folder regenerated.\n');
fprintf('PASS: COMPLETE GSL UDP SESSION VALIDATION.\n');
end
