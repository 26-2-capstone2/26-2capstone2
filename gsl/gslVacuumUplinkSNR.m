function snr_dB=gslVacuumUplinkSNR(fspl_dB,CFG)
% Uplink link budget before applying environmental attenuation.
eirp_dBW=CFG.groundTxPower_dBW+CFG.groundTxGain_dBi;
snr_dB=eirp_dBW+CFG.satelliteRxGT_dB_per_K-fspl_dB ...
    -10*log10(1.380649e-23)-10*log10(CFG.noiseBandwidth_Hz)-CFG.fixedImplementationLoss_dB;
end
