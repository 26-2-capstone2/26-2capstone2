function O=configGSLNStep(n)
if nargin<1,n=1;end
setupGSLNStep();O=configGSLTrendDDQN();O.nStep=n;
assert(ismember(n,[1 3 5]));
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,sprintf('results_n%d',n));
O.evaluationSeeds=20279301:20279310; % new held-out exploratory cohort
O.legacySeeds=20269301:20269310;
O.hysteresisMargins_dB=[0 .1 .3 .5];
assert(O.discountFactor==.95&&O.rewardWeights.onTime==1&&O.rewardWeights.burst==.3&&O.rewardWeights.handover==.1);
assert(isempty(intersect(O.trainingSeeds,O.evaluationSeeds)));
end
