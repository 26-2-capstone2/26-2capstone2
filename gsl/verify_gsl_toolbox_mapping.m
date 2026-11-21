function verify_gsl_toolbox_mapping()
C=configGSLToolboxPHY(); D=readtable(C.phyToolboxCurveFile);
[p,e,c,s,lo,hi]=getGSLToolboxPER(D.ebNo_dB,C); %#ok<ASGLU>
assert(max(abs(p-D.PER))<1e-12 && all(lo<=p+1e-12) && all(hi>=p-1e-12));
assert(all(s=="TOOLBOX_QPSK_AR4JA_AWGN_EMPIRICAL"));
assert(all(D.packets==D.packets(1)) && D.packets(1)>=100 && height(D)==42 && D.ebNo_dB(1)==-24 && D.ebNo_dB(end)==16);
[p,~,~,s]=getPERfromSNR([-25 17 NaN],C);
assert(all(isnan(p)) && s(1)=="TOOLBOX_OUTSIDE_MEASURED_CURVE" && s(3)=="MISSING_SNR");
C.noiseBandwidth_Hz=NaN;
[p,~,~,s]=getPERfromSNR(1,C); assert(isnan(p) && s=="MISSING_BANDWIDTH_OR_INFORMATION_RATE");
C=configGSLToolboxPHY(); C.noiseBandwidth_Hz=2*C.informationBitRate_bps;
[~,eb]=getPERfromSNR(0,C); assert(abs(eb-10*log10(2))<1e-12);
C.packetSize_bytes=150; caught=false;
try, getPERfromSNR(0,C); catch ex, caught=strcmp(ex.identifier,'GSL:ToolboxCurveConfiguration'); end
assert(caught,'GSL:CurveMismatchNotRejected');
fprintf('TOOLBOX CURVE / DISPATCH / UNITS / MISSING INPUT / OUTSIDE RANGE CHECK PASS\n');
end
