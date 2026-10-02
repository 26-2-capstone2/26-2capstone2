function per = getPERfromSNR(snr_dB)
% TODO: evidence-based QPSK + AR4JA rate 1/2 PER for this packet/frame length.
% Input is SNR=C/N, NOT Eb/N0. Document any conversion and curve domain.
% NaN means UNKNOWN. Never replace this with arbitrary loss probabilities.
per = nan(size(snr_dB));
end
