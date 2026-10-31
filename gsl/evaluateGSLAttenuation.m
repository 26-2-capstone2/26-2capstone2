function Q=evaluateGSLAttenuation(referenceL,C,environmentLoss_dB)
% Controlled link-margin experiment. No rain/cloud profile stacking, no ACM.
validateattributes(environmentLoss_dB,{'numeric'},{'scalar','finite','>=',0,'<=',20});
assert(ismember('vacuumSNR_dB',referenceL.Properties.VariableNames));
C.channelScenario='clear'; C.weather=weatherProfile('clear');
C.channelSigma_dB=0;
if ~isfield(C,'highSNRPolicy'), C.highSNRPolicy='ZERO_CWER'; end
if ~isfield(C,'lowSNRPolicy'), C.lowSNRPolicy='UNIT_CWER'; end
C.environmentLoss_dB=environmentLoss_dB;
C.experimentLabel=sprintf('Environment attenuation %.1f dB',environmentLoss_dB);
C.exportResults=false; C.makePlots=false;
L=referenceL;
% Discard prior atmospheric components: the slider is the total environment loss.
L.gasLoss_dB(:)=0; L.cloudLoss_dB(:)=0; L.rainLoss_dB(:)=0;
L.environmentLoss_dB=repmat(environmentLoss_dB,height(L),1);
L.atmosphericLoss_dB=repmat(environmentLoss_dB,height(L),1);
L.channelLoss_dB=L.atmosphericLoss_dB;
L.baseSNR_dB=L.vacuumSNR_dB-L.atmosphericLoss_dB;
L.snr_dB=L.baseSNR_dB;
L.weatherName=repmat("environment_attenuation",height(L),1);
P=simulatePacketTransmission(L,C);
P.environmentLoss_dB=repmat(environmentLoss_dB,height(P),1);
M=computePacketMetrics(P,C.rollingWindow_s);
Q=struct('config',C,'linkState',L,'packetTable',P,'packetMetrics',M);
end
