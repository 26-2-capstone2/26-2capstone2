function O=configGSLStability(mode)
if nargin<1,mode='control';end
setupGSLStability();O=configGSLTrendDDQN();O.mode=mode;O.targetTau=0;
O.numEpisodes=200;O.trainingSeeds=20269101:20269300;O.evaluationSeeds=20279301:20279310;
switch mode
    case 'control'
    case 'low_lr',O.learningRate=1e-4;
    case 'large_buffer',O.replayCapacity=60000;
    case 'soft_target',O.targetTau=.01;
    otherwise,error('Unknown mode');
end
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,['results_' mode]);
assert(isempty(intersect(O.trainingSeeds,O.evaluationSeeds)));
end
