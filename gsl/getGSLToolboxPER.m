function [per,ebNo,cwer,status,lower95,upper95]=getGSLToolboxPER(snr,CFG)
% Point estimates from actual 160 B packets; NO forced tail probabilities.
assert(strcmp(CFG.modulation,'QPSK') && strcmp(CFG.channelCoding,'CCSDS AR4JA') ...
    && CFG.codeRate==0.5 && CFG.informationBlockLength_bits==1024 && CFG.packetSize_bytes==160, ...
    'GSL:ToolboxCurveConfiguration','Rebuild the PHY curve for changed coding or packet size.');
per=nan(size(snr)); ebNo=per; cwer=per; lower95=per; upper95=per;
status=repmat("MISSING_BANDWIDTH_OR_INFORMATION_RATE",size(snr));
B=CFG.noiseBandwidth_Hz; R=CFG.informationBitRate_bps;
if isnan(B) || isnan(R), return; end
validateattributes(B,{'numeric'},{'scalar','positive','finite'});
validateattributes(R,{'numeric'},{'scalar','positive','finite'});
ebNo=snr+10*log10(B/R);
path=CFG.phyToolboxCurveFile;
assert(isfile(path),'GSL:MissingToolboxCurve','Run build_gsl_toolbox_phy_curve first.');
persistent cachedPath cachedStamp D
stamp=dir(path);
if isempty(D) || ~strcmp(cachedPath,path) || cachedStamp~=stamp.datenum
    D=readtable(path); cachedPath=path; cachedStamp=stamp.datenum;
    assert(height(D)==42 && D.ebNo_dB(1)==-24 && D.ebNo_dB(end)==16, ...
        'GSL:IncompleteToolboxCurve','Wait for all 42 PHY points before running GSL.');
    assert(all(diff(D.ebNo_dB)>0) && all(D.PER>=0 & D.PER<=1));
end
per=interp1(D.ebNo_dB,D.PER,ebNo,'linear',NaN);
cwer=interp1(D.ebNo_dB,D.CWER,ebNo,'linear',NaN);
lower95=interp1(D.ebNo_dB,D.PER_lower95,ebNo,'linear',NaN);
upper95=interp1(D.ebNo_dB,D.PER_upper95,ebNo,'linear',NaN);
status(:)="TOOLBOX_OUTSIDE_MEASURED_CURVE";
status(isfinite(per))="TOOLBOX_QPSK_AR4JA_AWGN_EMPIRICAL";
status(~isfinite(snr))="MISSING_SNR";
end
