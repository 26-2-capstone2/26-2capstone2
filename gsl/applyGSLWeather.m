function L=applyGSLWeather(L,C)
% Integrate finite atmospheric/cloud/rain layers, not the whole satellite path.
W=C.weather; f=C.carrierFrequency_Hz/1e9;
assert(ismember(string(C.channelScenario),["clear","cloudy","rainy"]));
assert(strcmp(W.name,C.channelScenario),'Use configGSL(weatherName) to select a profile.');
assert(W.cloudTopAGL_m>W.cloudBaseAGL_m && W.layerStep_m>0);
validateattributes(W.rainRate_mm_h,{'numeric'},{'scalar','nonnegative','finite'});
validateattributes(W.cloudWaterDensity_g_m3,{'numeric'},{'scalar','nonnegative','finite'});
el=L.elevation_deg; valid=isfinite(el) & el>=C.minElevation_deg;
ev=el(valid); r0=C.earthEquatorialRadius_m+C.gsAltitude_m;
distance=@(h)sqrt((r0*sind(ev)).^2+2*r0*h+h*h)-r0*sind(ev);
edges=0:W.layerStep_m:W.atmosphereTopAGL_m;
if edges(end)<W.atmosphereTopAGL_m, edges(end+1)=W.atmosphereTopAGL_m; end
gas=zeros(size(ev)); T0=W.surfaceTemperature_C+273.15;
% Hydrostatic lapse-rate troposphere; isothermal above 11 km.
for j=1:numel(edges)-1
    h=mean(edges(j:j+1)); z=min(h,11000); lapse=W.lapseRate_K_km/1000;
    T=T0-lapse*z;
    pTotal=W.surfacePressure_Pa/100*(T/T0)^(9.80665/(287.05*lapse));
    if h>11000, pTotal=pTotal*exp(-9.80665*(h-11000)/(287.05*T)); end
    rho=W.surfaceVaporDensity_g_m3*exp(-h/W.vaporScaleHeight_m);
    dry=pTotal-rho*T/216.7; assert(dry>0);
    gamma=ituGasSpecific(f,T,dry,rho);
    gas=gas+gamma*(distance(edges(j+1))-distance(edges(j)))/1000;
end
Tc=T0-W.lapseRate_K_km*mean([W.cloudBaseAGL_m W.cloudTopAGL_m])/1000;
cloud=ituCloudSpecific(f,Tc,W.cloudWaterDensity_g_m3)* ...
    (distance(W.cloudTopAGL_m)-distance(W.cloudBaseAGL_m))/1000;
rain=ituRainSpecific(f,W.rainRate_mm_h,ev,W.polarizationTilt_deg).*distance(W.rainTopAGL_m)/1000;
n=height(L); L.gasLoss_dB=nan(n,1); L.cloudLoss_dB=nan(n,1); L.rainLoss_dB=nan(n,1);
L.gasLoss_dB(valid)=gas; L.cloudLoss_dB(valid)=cloud; L.rainLoss_dB(valid)=rain;
L.atmosphericLoss_dB=L.gasLoss_dB+L.cloudLoss_dB+L.rainLoss_dB;
L.txEIRP_dBW=repmat(C.groundTxPower_dBW+C.groundTxGain_dBi,n,1);
L.vacuumSNR_dB=L.txEIRP_dBW+C.satelliteRxGT_dB_per_K-L.fspl_dB ...
    -10*log10(1.380649e-23)-10*log10(C.noiseBandwidth_Hz)-C.fixedImplementationLoss_dB;
L.baseSNR_dB=L.vacuumSNR_dB-L.atmosphericLoss_dB;
L.snr_dB=L.baseSNR_dB; L.channelLoss_dB=L.atmosphericLoss_dB;
L.weatherName=repmat(string(W.name),n,1);
end
