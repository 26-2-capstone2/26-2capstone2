function O=configGSLPeakReward(mode)
if nargin<1,mode='peak';end
assert(ismember(mode,{'control','peak'}));
O=configGSLQContext();O.rewardMode=mode;
O.discountFactor=1; % finite fixed 600-step episode: all packet times weighted equally
O.rewardWeights.handover=0; % physical 100ms HO interruption remains unchanged
O.featureNames{13}='runningMaxLoss/(runningMaxLoss+60)';
O.featureNames{14}='remainingEpisodeTime/600';
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,['results_' mode]);
O.validationSeeds=20278001:20278010;
O.rewardDescription='negative packet-loss fraction minus 0.3 times burst cost; no extra HO term';
end
