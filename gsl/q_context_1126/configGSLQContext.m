function O=configGSLQContext()
O=configGSLTrendDDQN();
O.numEpisodes=100;O.trainingSeeds=20269101:20269200;
O.featureNames{12}='bestVisibleEstimatedSuccess';
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,'results_context');
O.initialization='original 11-input seeded weights; added input column initialized to zero';
end
