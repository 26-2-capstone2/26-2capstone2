function [per,ebNo_dB,pCW,status] = getPERfromSNR(snr_dB,CFG)
% C/N to INFORMATION Eb/N0, then source-backed AR4JA CWER lookup.
% Missing mapping / outside published support remains NaN. No extrapolation.
assert(strcmp(CFG.modulation,'QPSK') && strcmp(CFG.channelCoding,'CCSDS AR4JA') ...
    && CFG.codeRate==1/2 && CFG.informationBlockLength_bits==1024,'GSL:PHYConfiguration');
per=nan(size(snr_dB)); ebNo_dB=per; pCW=per;
status=repmat("MISSING_BANDWIDTH_OR_INFORMATION_RATE",size(snr_dB));
B=CFG.noiseBandwidth_Hz; Rb=CFG.informationBitRate_bps;
assert(isscalar(B) && isscalar(Rb) && isreal(B) && isreal(Rb) && ...
    (isnan(B) || (isfinite(B) && B>0)) && (isnan(Rb) || (isfinite(Rb) && Rb>0)), ...
    'GSL:PHYUnits','Bandwidth and information rate must be positive or NaN.');
if isnan(B) || isnan(Rb), return; end
assert(strlength(strtrim(string(CFG.phyMappingSource)))>0,'GSL:MissingPHYMappingSource', ...
    'Document the source of noise bandwidth and information-rate interpretation.');
ebNo_dB=snr_dB+10*log10(B/Rb);
D=readtable(fullfile(fileparts(mfilename('fullpath')),'ar4ja_r12_k1024_cwer.csv'));
assert(all(diff(D.ebNo_dB)>0) && all(D.codewordErrorRate>0 & D.codewordErrorRate<=1));
% Interpolate ONLY within the digitized JPL curve; never extrapolate.
minEbNo=D.ebNo_dB(1); maxEbNo=D.ebNo_dB(end);
valid=isfinite(ebNo_dB);
inside=valid & ebNo_dB>=minEbNo & ebNo_dB<=maxEbNo;
above=valid & ebNo_dB>maxEbNo;
below=valid & ebNo_dB<minEbNo;
pCW(inside)=10.^interp1(D.ebNo_dB,log10(D.codewordErrorRate),ebNo_dB(inside),'linear');
status(:)="MISSING_SNR";
status(below)="BELOW_PUBLISHED_CURVE";
status(inside)="JPL_FIGURE14_LOOKUP";
status(above)="ABOVE_PUBLISHED_CURVE_UNRESOLVED";
% Explicit network-level approximation for a finite 600-s baseline.
% pCW=0 here means no simulated observable errors, NOT a measured or
% mathematically zero physical CWER. Published upper-end packet PER
% (using two independent codewords for 160 B) is ~3.42e-7.
if isfield(CFG,'highSNRPolicy') && strcmp(CFG.highSNRPolicy,'ZERO_OBSERVABLE_ERRORS')
    pCW(above)=0;
    status(above)="HIGH_SNR_BELOW_RESOLUTION";
end
blocks=ceil(CFG.packetSize_bytes*8/CFG.informationBlockLength_bits);
known=isfinite(pCW);
per(known)=-expm1(blocks*log1p(-pCW(known)));
end
