function T=census_candidate_context()
% Policy-independent count of candidate-set quality across TRAINING seeds.
here=fileparts(mfilename('fullpath'));O=configGSLQContext();C=O.baseConfig;C.numPlanes=6;C.satsPerPlane=11;
C.makePlots=false;C.openViewer=false;C.openPacketViewer=false;C.exportResults=false;
G=buildGSLSelectionGeometry(C);T=table();
for seed=O.trainingSeeds
    env=GSLTrendEpisode(C,G,O,seed);success=1-env.per;success(~G.isVisible)=-Inf;
    best=max(success(1:C.duration_s,:),[],2);visible=any(G.isVisible(1:C.duration_s,:),2);
    assert(all(visible));
    row=table(seed,sum(best==0),sum(best>0&best<.1),sum(best>=.1&best<.9),sum(best>=.9), ...
        'VariableNames',{'seed','allCandidatesPER1_seconds','bestSuccess0to0_1_seconds', ...
        'bestSuccess0_1to0_9_seconds','bestSuccessAtLeast0_9_seconds'});
    T=[T;row]; %#ok<AGROW>
end
writetable(T,fullfile(here,'training_candidate_context_census.csv'));
disp(sum(T{:,2:end},1));fprintf('CONTEXT CENSUS PASS: 100 training seeds, 60000 decision times, no policy changes.\n');
end
