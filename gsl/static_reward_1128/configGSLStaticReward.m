function O=configGSLStaticReward()
setupStaticReward();O=configGSLTrendDDQN();O.baseConfig=configGSLStaticFront();
O.numEpisodes=100;O.trainingSeeds=20281001:20281100;
O.evaluationSeeds=20282001:20282010;
O.agentSeed=20261123;O.epsilonDecaySteps=48000;
O.trainingQMargin=.02;O.evaluationQMargins=[0 .02];
O.maxSNRMargin_dB=.1;
O.rewardDefinitions(1)=struct('name','linear','onTime',1,'burst',.3,'L0',60,'power',1,'cap',10,'handover',.1);
O.rewardDefinitions(2)=struct('name','quadratic','onTime',1,'burst',.15,'L0',12,'power',2,'cap',25,'handover',.03);
O.resultRoot=fullfile(fileparts(mfilename('fullpath')),'results');
O.makePlots=true;O.smoke=false;
end
