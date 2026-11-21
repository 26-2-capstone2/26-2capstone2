function O=configGSLThreeConstellations()
% Scope: ground station -> first receiving satellite ONLY.
O.sizes=[6 11;20 20;36 36];
O.baseConfig=configGSLToolboxPHY();
O.environmentLoss_dB=8;
O.hysteresis_dB=0.1; % Max-SNR baseline gate
O.qHysteresis=0.02; % DDQN Q-value margin, NOT dB
O.numEpisodes=30; % 10 per grid, interleaved; one shared candidate scoring net
O.trainingSeeds=20267001:20267030;
O.evaluationSeeds=20268001:20268010;
O.agentSeed=20261121;
O.batchSize=64; O.replayCapacity=20000; O.warmupSteps=512;
O.trainEvery=8; O.targetUpdateEvery=100;
O.learningRate=3e-4; O.discountFactor=.95; O.gradientThreshold=5;
O.epsilonStart=1; O.epsilonEnd=.05; O.epsilonDecaySteps=12000;
O.rewardWeights=struct('onTime',1,'burst',.3,'handover',.1);
O.featureNames={'snr/10','snrDelta/2','elevation/90','isServing','hasHistory', ...
    'estimatedSuccess','observedStreak/(streak+60)','servingSNR/10', ...
    'snrAdvantage/5','visibleFraction'};
O.root=fileparts(mfilename('fullpath'));
O.cacheDir=fullfile(O.root,'geometry_cache');
O.resultRoot=fullfile(O.root,'results_three_constellations');
end
