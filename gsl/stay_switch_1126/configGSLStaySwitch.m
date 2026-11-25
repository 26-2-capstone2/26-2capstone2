function O=configGSLStaySwitch()
O=configGSLQContext();
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,'results_paired');
O.criticalSuccessThreshold=.1; % classification only, not a PHY threshold
O.rareReplayCapacity=2048;O.rareBatchQuota=8; % 8 paired experiences + 56 ordinary, total 64
O.validationSeeds=20276001:20276010;
% Quota fixed before results. No validation transitions enter either replay buffer.
end
