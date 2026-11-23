function O=configGSLTrendDDQN()
O=configGSLThreeConstellations();
O.sizes=[6 11];O.environmentLoss_dB=6;
O.numEpisodes=100;O.trainingSeeds=20269101:20269200;
O.evaluationSeeds=20269301:20269310;O.agentSeed=20261123;
O.epsilonDecaySteps=48000; % 80 training episodes, then epsilon=0.05
O.featureNames{11}='causalLast5sMeanSNRDelta/2';
O.qHysteresis=.02; % same Q-value gate as initial model; NOT 0.02 dB
O.root=fileparts(mfilename('fullpath'));
O.resultRoot=fullfile(O.root,'results_ddqn_6x11');
assert(isempty(intersect(O.trainingSeeds,O.evaluationSeeds)));
end
