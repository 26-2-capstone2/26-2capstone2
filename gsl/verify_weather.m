function verify_weather()
% Independent ITU reference values + channel/packet integration invariants.
[~,kh,ah]=ituRainSpecific(14,1,0,0);
assert(abs(kh-.03738)<5e-6 && abs(ah-1.1396)<5e-4,'P.838 Table 5 horizontal reference');
[~,kv,av]=ituRainSpecific(14,1,0,90);
assert(abs(kv-.04126)<5e-6 && abs(av-1.0646)<5e-4,'P.838 Table 5 vertical reference');
assert(ituRainSpecific(14,0,45,45)==0 && ituCloudSpecific(14,283.15,0)==0);
assert(ituGasSpecific(14,288.15,1013.25,7.5)>ituGasSpecific(14,288.15,1013.25,0));
C=configGSL(); C.duration_s=2;
L=table((0:2).',[1;2;2],true(3,1),[false;true;false], ...
    [25;45;90],3*ones(3,1),175*ones(3,1), ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent','elevation_deg','propagationDelay_ms','fspl_dB'});
names=["clear","cloudy","rainy"]; A=cell(3,1); P=cell(3,1);
for j=1:3
    C=configGSL(names(j)); C.duration_s=2; A{j}=applyGSLWeather(L,C);
    P{j}=simulatePacketTransmission(A{j},C);
    assert(all(P{j}.syntheticFade_dB==0) && all(P{j}.channelPerturbation_dB==0));
    assert(all(A{j}.atmosphericLoss_dB>=0));
    assert(A{j}.atmosphericLoss_dB(1)>A{j}.atmosphericLoss_dB(3));
    assert(all(abs(A{j}.vacuumSNR_dB-A{j}.snr_dB-A{j}.atmosphericLoss_dB)<1e-10));
end
assert(all(A{1}.cloudLoss_dB==0) && all(A{1}.rainLoss_dB==0));
assert(all(A{2}.cloudLoss_dB>0) && all(A{2}.rainLoss_dB==0));
assert(all(A{3}.rainLoss_dB>0));
assert(all(A{1}.snr_dB>A{2}.snr_dB) && all(A{2}.snr_dB>A{3}.snr_dB));
assert(isequal(P{1}.phyRandomDraw,P{3}.phyRandomDraw));
assert(isequal(P{1}.handover_loss,P{3}.handover_loss));
fprintf('PASS verify_weather: ITU reference coefficients; gas/cloud/rain separation; geometry; units; no artificial fades; matched traffic/handovers/random draws.\n');
end
