function verify_gsl_peak_reward()
O=configGSLPeakReward('peak');C=O.baseConfig;C.duration_s=12;C.makePlots=false;
G=buildGSLSelectionGeometry(C);P=GSLPeakEpisode(C,G,O,20279990);
Q=O;Q.rewardMode='control';A=GSLPeakEpisode(C,G,Q,20279990);
B=GSLContextEpisode(C,G,Q,20279990);
for t=0:11
    S=P.observe();T=A.observe();U=B.observe();
    assert(isequal(S.features,T.features)&&isequal(S.features(1:12,:),U.features));
    assert(all(S.features(14,:)==single(1-t/12)));
    id=S.ids(1);[~,rp]=P.step(id);[~,ra]=A.step(id);[~,rb]=B.step(id);
    assert(isequal(P.loss,A.loss)&&isequal(P.loss,B.loss));
    assert(abs(ra-(rb-1))<1e-10); % same paths, no late arrivals here
    assert(rp<=eps&&ra<=eps);
end
M=max(P.stepMaxRun);assert(sum(P.peakIncrements)==M);
assert(abs(sum(P.objectiveRewardHistory)+(sum(P.loss)+.3*M)/60)<1e-10);
assert(isequal(size(P.observe().features),[14 0]));
% Identical old weights plus zero new-input columns at initialization.
old=GSLContextDoubleDQN(O);new=GSLPeakDoubleDQN(O);
S=struct('ids',[1;2],'features',single(reshape(sin(1:24),12,2)));T=S;T.features=[T.features;zeros(2,2,'single')];
assert(max(abs(double(old.values(S))-double(new.values(T))))<2e-6);
O.batchSize=4;O.warmupSteps=4;O.replayCapacity=10;O.targetUpdateEvery=1;new=GSLPeakDoubleDQN(O);
for k=1:8
    S=struct('ids',[1;2],'features',single(ones(14,2)*k/10));T=S;
    if mod(k,3)==0,T.ids=zeros(0,1);T.features=zeros(14,0,'single');end
    new.remember(S,1,-k/100,T,mod(k,3)==0);
end
assert(isfinite(new.learn())&&new.updateCount==1);
% Frozen-trajectory algebra: no primary Pareto-dominated action can be preferred.
gsl=fileparts(fileparts(mfilename('fullpath')));
D=readtable(fullfile(gsl,'reward_audit_1126','full_episode_audit','full_episode_pairs.csv'));
delta=-(D.switchFullLoss-D.stayFullLoss+.3*(D.switchFullMaxRun-D.stayFullMaxRun))/60;
bad=(delta>1e-9&D.switchFullLoss>=D.stayFullLoss&D.switchFullMaxRun>=D.stayFullMaxRun) ...
    |(delta< -1e-9&D.stayFullLoss>=D.switchFullLoss&D.stayFullMaxRun>=D.switchFullMaxRun);
assert(~any(bad));
out=table(D.seed,D.time_s,D.stayFullLoss,D.switchFullLoss,D.stayFullMaxRun,D.switchFullMaxRun,delta, ...
    'VariableNames',{'seed','time_s','stayLoss','switchLoss','stayMax','switchMax','newSwitchMinusStayReturn'});
writetable(out,fullfile(fileparts(mfilename('fullpath')),'fixed_trajectory_peak_scores.csv'));
fprintf('PEAK REWARD PASS: unchanged packets, sufficient causal state, telescoping episode cost, original-weight initialization, gradient, Pareto alignment.\n');
end
