function B=main_gsl_weather_comparison(CFG)
% Three weather cases, one constellation geometry, same traffic and PHY draws.
if nargin==0, CFG=configGSL(); end
base=CFG; base.enablePackets=false; base.openViewer=false;
base.openPacketViewer=false; base.makePlots=false; base.exportResults=false;
R=main_gsl_simulation(base);
B=compareGSLWeather(R.linkState,CFG);
end
