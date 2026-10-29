function verify_weather_window(B)
% Exercise the exact popup callback, including packet grid synchronization.
if nargin==0
    C=configGSL(); C.duration_s=6; C.makePlots=false; C.exportResults=false;
    L=table((0:6).',ones(7,1),true(7,1),false(7,1), ...
        linspace(25,70,7).',3*ones(7,1),173*ones(7,1), ...
        'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','elevation_deg','propagationDelay_ms','fspl_dB'});
    B=compareGSLWeather(L,C);
end
names=["clear","cloudy","rainy"];
for name=names, B.(name).config.exportResults=false; end
Q=B.clear; C=Q.config; C.makePlots=true;
plotResults(Q.linkState,Q.packetTable,Q.packetMetrics,C);
plotUplinkDiagnostics(Q.linkState,Q.packetTable,Q.packetMetrics,C);
f=attachGSLWeatherResults(B,C); H=getappdata(f,'GSLPacketPlotHandles');
d=findall(groot,'Name','GSL Uplink - Channel and Loss Runs');
D=getappdata(d,'GSLDiagnosticPlotHandles');
pv=GSLPacketViewer(Q.packetTable,Q.linkState,C,[],C.startTime);
guard=onCleanup(@()delete(pv)); %#ok<NASGU>
pv.setTime(1.25); frames=pv.CurrentTime_s;
count=numel(findall(groot,'Type','figure')); popup=getappdata(f,'GSLWeatherSelector');
for k=1:3
    popup.Value=k; cb=popup.Callback; cb(popup,[]);
    assert(isgraphics(f) && numel(findall(groot,'Type','figure'))==count);
    assert(getappdata(f,'GSLSelectedWeather')==names(k));
    assert(isequal(H.onTime.YData(:),B.(names(k)).packetMetrics.rollingOnTimeDeliveryRate_pct(:)));
    assert(isequal(D.snr.YData(:),B.(names(k)).packetTable.snr_dB(:)));
    assert(pv.WeatherName==names(k) && pv.CurrentTime_s==frames);
end
fprintf('PASS weather window: original figure/plot handles reused; popup switches all three cases, diagnostic SNR and packet grid; time unchanged.\n');
end
