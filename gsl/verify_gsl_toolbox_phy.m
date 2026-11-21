function verify_gsl_toolbox_phy()
C=gslAR4JACodec();
fprintf('AR4JA graph PASS: %d checks, %d variables, %d edges\n',size(C.H,1),size(C.H,2),nnz(C.H));
tic; a=simulateGSLPHYBatch(Inf,20,20261121);
assert(a.packetErrors==0 && a.bitErrors==0,'GSL:NoiselessPHY');
fprintf('Noiseless QPSK/AR4JA packet round-trip PASS (20 packets)\n');
for eb=[-2 0 1 2 4]
    t=tic; a=simulateGSLPHYBatch(eb,50,20261121);
    fprintf('EbNo=%+.1f dB: PER=%.4f (%d/%d), mean iterations=%.1f, %.2f s\n', ...
        eb,a.packetErrors/a.packets,a.packetErrors,a.packets,a.meanIterations,toc(t));
end
fprintf('PHY PILOT COMPLETE\n');
end
