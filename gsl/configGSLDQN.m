function O=configGSLDQN()
% Experimental starting settings. Tune on validation seeds, then freeze for test.
O.numEpisodes=20;
O.batchSize=64;
O.replayCapacity=20000;
O.warmupSteps=512;
O.trainEvery=4;
O.targetUpdateEvery=100; % gradient updates, not environment steps
O.learningRate=1e-3;
O.discountFactor=0.99;
O.gradientThreshold=5;
O.epsilonStart=1;
O.epsilonEnd=0.05;
O.epsilonDecaySteps=10000;
O.agentSeed=20261112;
O.trainingSeeds=20262001:20262020;
O.evaluationSeeds=20263001:20263003;
O.rewardWeights=struct('onTime',1,'burst',0.5,'handover',0.05);
O.makePlots=true;
O.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_ddqn', ...
    char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));
end
