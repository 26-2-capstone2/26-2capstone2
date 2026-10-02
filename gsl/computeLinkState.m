function L = computeLinkState(G,sats,CFG)
% Ku-band DOWNLINK reference; no interference/atmospheric/pointing losses.
% Link availability here means serving+visibility, not an SNR threshold.
[id,ho] = selectServingSatellite(G.elevation_deg,G.isVisible,CFG.handoverMargin_deg);
n = numel(id); valid = id>0; elev = nan(n,1); range = elev;
idx = sub2ind(size(G.elevation_deg),find(valid),id(valid));
elev(valid) = G.elevation_deg(idx); range(valid) = G.slantRange_m(idx);
c_mps = 299792458; k_W_per_K_Hz = 1.380649e-23; % exact SI constants
validateattributes(CFG.carrierFrequency_Hz,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.signalToNoiseBandwidthRatio,{'numeric'},{'scalar','positive','finite'});
fspl = 20*log10(4*pi*range*CFG.carrierFrequency_Hz/c_mps);
% SNR = EIRP_density[dBW/Hz] + G/T - FSPL - 10log10(k) + 10log10(Bs/Bn).
% EIRP_density[dBW/Hz] = EIRP_density[dBW/MHz] - 60.
snr = CFG.txEIRPDensity_dBW_per_MHz-60+CFG.rxGT_dB_per_K-fspl ...
    -10*log10(k_W_per_K_Hz)+10*log10(CFG.signalToNoiseBandwidthRatio);
radial = nan(n,1);
% Fixed ground station has zero velocity in ECEF. states removes Earth rotation.
a = CFG.earthEquatorialRadius_m; f = 1/298.257223563;
e2 = f*(2-f); lat = deg2rad(CFG.gsLatitude_deg); lon = deg2rad(CFG.gsLongitude_deg);
N = a/sqrt(1-e2*sin(lat)^2); h = CFG.gsAltitude_m;
gsECEF = [(N+h)*cos(lat)*cos(lon); (N+h)*cos(lat)*sin(lon); (N*(1-e2)+h)*sin(lat)];
for s = unique(id(valid)).'
    [p,v] = states(sats(s),'CoordinateFrame','ecef');
    p = reshape(p,3,[]); v = reshape(v,3,[]);
    assert(size(p,2)==n,'GSL:StatesTime','Unexpected states time grid.');
    rows = find(id==s); los = p(:,rows)-gsECEF;
    distance = vecnorm(los);
    assert(max(abs(distance(:)-range(rows)))<1,'GSL:Range','ECEF and aer range mismatch.');
    radial(rows) = sum(v(:,rows).*(los./distance),1).';
end
doppler = -(radial/c_mps)*CFG.carrierFrequency_Hz;
residual = nan(n,1); residual(valid)=0; % ideal compensation; no SNR penalty
L = table(G.time_s,id,valid,ho,elev,range,1000*range/c_mps,fspl,snr, ...
    radial,doppler,residual,'VariableNames',{'time_s','servingSatID', ...
    'isLinkAvailable','handoverEvent','elevation_deg','slantRange_m', ...
    'propagationDelay_ms','fspl_dB','snr_dB','radialVelocity_mps', ...
    'rawDoppler_Hz','residualDoppler_Hz'});
end
