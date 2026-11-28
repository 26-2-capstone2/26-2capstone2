function T=probe_regression_case()
gsl=setupGSLCheckpointAudit();here=fileparts(mfilename('fullpath'));
addpath(fullfile(gsl,'burst_counterfactual_1127'));
source=fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356');
D=load(fullfile(source,'study.mat'),'R');C=configGSLToolboxPHY(D.R.config);D=load(fullfile(source,'geometry.mat'),'geometry');G=D.geometry;
D=load(fullfile(source,'agent_episode_0200.mat'),'checkpoint');O=D.checkpoint.options;agent=GSLTrendDoubleDQN(O);agent.restore(D.checkpoint);
seed=20279302;original=GSLTrendAuditEpisode(C,G,O,seed);
S=original.observe();original.step(pick(agent,S,O.qHysteresis));assert(original.servingID==44);
S=original.observe();q=agent.values(S);id=pick(agent,S,O.qHysteresis);assert(id==64);
alternative=copy(original);original.step(id);alternative.step(44);
originalFirstReward=original.rewardHistory(2);alternativeFirstReward=alternative.rewardHistory(2);
while original.time<600,S=original.observe();original.step(pick(agent,S,O.qHysteresis));end
while alternative.time<600,S=alternative.observe();alternative.step(pick(agent,S,O.qHysteresis));end
saved=load(fullfile(here,'results/episode_0200_repeat_02/preview.mat'),'preview');assert(isequal(original.loss,logical(saved.preview.P.lost)));
discount=O.discountFactor.^(0:598).';origReturn=sum(original.rewardHistory(2:end).*discount);altReturn=sum(alternative.rewardHistory(2:end).*discount);
S0=GSLTrendAuditEpisode(C,G,O,seed);S=S0.observe();S0.step(pick(agent,S,O.qHysteresis));S=S0.observe();q=agent.values(S);
origIx=find(S.ids==64);altIx=find(S.ids==44);
T=table([64;44],[q(origIx);q(altIx)],[original.per(2,64);alternative.per(2,44)], ...
    [originalFirstReward;alternativeFirstReward],[origReturn;altReturn], ...
    [sum(original.loss);sum(alternative.loss)],[maxRun(original.loss);maxRun(alternative.loss)], ...
    [sum(original.handovers);sum(alternative.handovers)], ...
    'VariableNames',{'forcedSatIDAt1s','predictedQAtSameState','PERAt1s','firstSecondReward','sampledDiscountedReturnFrom1s','fullLost','fullMaxRun','handovers'});
writetable(T,fullfile(here,'results/regression_case_200_repeat02.csv'));
U=table((1:36000).',original.loss,alternative.loss,'VariableNames',{'packetID','originalLost','stay44Lost'});writetable(U,fullfile(here,'results/regression_case_packets.csv'));
disp(T);fprintf('REGRESSION CASE PASS: same state/draws, change only action at t=1, then original 200-episode frozen policy. Sampled return is NOT ground-truth expected Q.\n');
end
function id=pick(agent,S,margin)
id=0;if isempty(S.ids),return;end
q=agent.values(S);[~,j]=max(q);old=find(S.features(4,:)>0,1);if ~isempty(old)&&q(j)<q(old)+margin,j=old;end;id=S.ids(j);
end
function m=maxRun(lost)
e=diff([false;logical(lost(:));false]);v=find(e==-1)-find(e==1);m=0;if ~isempty(v),m=max(v);end
end
