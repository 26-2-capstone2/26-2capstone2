function verify_attenuation_slider
% Accounting / monotonic paired PHY / exact UI callback / same playback clock.
C=configGSL(); C.duration_s=6; C.makePlots=false; C.exportResults=false;
L=table((0:6).',ones(7,1),true(7,1),false(7,1), ...
    45*ones(7,1),3*ones(7,1),173*ones(7,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','elevation_deg','propagationDelay_ms','fspl_dB'});
L.handoverEvent(4)=true;
B=compareGSLWeather(L,C);
ref=B.clear.linkState;
% Fix Eb/N0 to a known fixture; weather calculations are tested separately.
ref.vacuumSNR_dB=9*ones(height(ref),1);
B.clear.linkState=ref;
q0=evaluateGSLAttenuation(ref,C,0);
q1=evaluateGSLAttenuation(ref,C,7);
q2=evaluateGSLAttenuation(ref,C,8);
q3=evaluateGSLAttenuation(ref,C,20);
assert(q0.packetMetrics.pendingPackets==0);
assert(q0.packetMetrics.receivedPackets==q0.packetMetrics.attemptedPackets);
assert(q1.packetMetrics.pendingPackets==0 && q2.packetMetrics.pendingPackets==0);
assert(q3.packetMetrics.pendingPackets==0 && q3.packetMetrics.lostPackets==height(q3.packetTable));
assert(all(q0.packetTable.phyStatus(q0.packetTable.attempted)=="HIGH_SNR_ZERO_CWER_ASSUMPTION"));
assert(all(q3.packetTable.phyStatus(q3.packetTable.attempted)=="LOW_SNR_UNIT_CWER_ASSUMPTION"));
strict=C; strict.highSNRPolicy='UNRESOLVED'; strict.lowSNRPolicy='UNRESOLVED';
qs=evaluateGSLAttenuation(ref,strict,0);
assert(qs.packetMetrics.pendingPackets==qs.packetMetrics.attemptedPackets);
% Published endpoints remain lookup values, only strictly external points saturate.
T=readtable(fullfile(fileparts(mfilename('fullpath')),'ar4ja_r12_k1024_cwer.csv'));
[p,~,~,st]=getPERfromSNR([-1;T.ebNo_dB(1);T.ebNo_dB(end);3],C);
assert(p(1)==1 && p(4)==0 && all(st(2:3)=="JPL_FIGURE14_LOOKUP"));
assert(isequal(q1.packetTable.phyRandomDraw,q2.packetTable.phyRandomDraw));
assert(all(q2.packetTable.snr_dB==q1.packetTable.snr_dB-1));
assert(all(q2.packetTable.phyPER>=q1.packetTable.phyPER | ~q1.packetTable.attempted));
assert(all(~(q1.packetTable.phy_loss==1) | q2.packetTable.phy_loss==1));
assert(q1.config.linkDataRate_bps==C.linkDataRate_bps);
assert(q1.packetMetrics.generatedPackets-q1.packetMetrics.receivedPackets== ...
    q1.packetMetrics.phyLossPackets+q1.packetMetrics.handoverLossPackets+q1.packetMetrics.outageLossPackets);
plotResults(B.clear.linkState,B.clear.packetTable,B.clear.packetMetrics,C);
plotUplinkDiagnostics(B.clear.linkState,B.clear.packetTable,B.clear.packetMetrics,C);
f=attachGSLWeatherResults(B,C);
pv=GSLPacketViewer(B.clear.packetTable,B.clear.linkState,C,[],C.startTime);
guard=onCleanup(@()delete(pv)); %#ok<NASGU>
pv.setTime(1.25); count=numel(findall(groot,'Type','figure'));
s=findall(f,'Tag','GSLAttenuationSlider');
for value=[0 7 8 20]
    s.Value=value; cb=s.Callback; cb(s,[]);
    A=getappdata(f,'GSLWeatherCases'); Q=A.manual;
    assert(Q.config.environmentLoss_dB==value);
    assert(getappdata(f,'GSLSelectedWeather')=="manual");
    assert(pv.CurrentTime_s==1.25 && contains(pv.WeatherName,'Environment'));
    assert(numel(findall(groot,'Type','figure'))==count);
    H=getappdata(f,'GSLPacketPlotHandles');
    assert(isequaln(H.onTime.YData(:),Q.packetMetrics.rollingOnTimeDeliveryRate_pct));
end
popup=getappdata(f,'GSLWeatherSelector'); popup.Value=2; cb=popup.Callback; cb(popup,[]);
assert(getappdata(f,'GSLSelectedWeather')=="cloudy" && pv.CurrentTime_s==1.25);
fprintf('PASS attenuation: explicit saturation, lookup endpoints, strict option, paired monotonic losses, accounting, same figures/time.\n');
end
