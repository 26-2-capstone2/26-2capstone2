function Q=evaluateGSLAttenuation(referenceL,C,extraLoss_dB)
% Controlled link-margin experiment. No rain/cloud profile stacking, no ACM.
validateattributes(extraLoss_dB,{'numeric'},{'scalar','finite','>=',0,'<=',20});
assert(ismember('vacuumSNR_dB',referenceL.Properties.VariableNames));
C.channelScenario='clear'; C.weather=weatherProfile('clear');
C.channelSigma_dB=0; C.highSNRPolicy='UNRESOLVED'; C.lowSNRPolicy='UNRESOLVED';
C.manualExtraLoss_dB=extraLoss_dB;
C.experimentLabel=sprintf('Manual extra attenuation %.1f dB',extraLoss_dB);
C.exportResults=false; C.makePlots=false;
L=referenceL;
% referenceL is the clear-sky case: retain ONLY its gas absorption.
L.cloudLoss_dB(:)=0; L.rainLoss_dB(:)=0;
L.manualExtraLoss_dB=repmat(extraLoss_dB,height(L),1);
L.atmosphericLoss_dB=L.gasLoss_dB+extraLoss_dB;
L.channelLoss_dB=L.atmosphericLoss_dB;
L.baseSNR_dB=L.vacuumSNR_dB-L.atmosphericLoss_dB;
L.snr_dB=L.baseSNR_dB;
L.weatherName=repmat("manual_attenuation",height(L),1);
P=simulatePacketTransmission(L,C);
P.manualExtraLoss_dB=repmat(extraLoss_dB,height(P),1);
M=computePacketMetrics(P,C.rollingWindow_s);
Q=struct('config',C,'linkState',L,'packetTable',P,'packetMetrics',M);
end
