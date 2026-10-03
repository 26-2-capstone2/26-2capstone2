function per=getPERfromSNR(snr_dB,packetBytes,noiseBandwidth_Hz,bitRate_bps)
% Ideal uncoded coherent BPSK/AWGN REFERENCE, not a validated Starlink PER.
% SNR=C/N; Eb/N0 = (C/N)*Bnoise/Rbit. Independent bit errors assumed.
if nargin<2, packetBytes=160; end
if nargin<3, noiseBandwidth_Hz=50e6; end
if nargin<4, bitRate_bps=50e6; end
validateattributes(packetBytes,{'numeric'},{'scalar','positive','integer'});
validateattributes(noiseBandwidth_Hz,{'numeric'},{'scalar','positive','finite'});
validateattributes(bitRate_bps,{'numeric'},{'scalar','positive','finite'});
ebn0=10.^(snr_dB/10)*noiseBandwidth_Hz/bitRate_bps;
ber=0.5*erfc(sqrt(ebn0));
% Stable equivalent of 1-(1-BER)^(8*packetBytes), including very small BER.
per=-expm1(8*packetBytes*log1p(-ber));
end
