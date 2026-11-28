function B=gslStaySwitchPair(env,S,threshold)
% Two exact simulator transitions from the same pre-action state.
% Threshold classifies training experiences; it never changes PHY or action legality.
if nargin<2,S=env.observe();end
if nargin<3,threshold=.1;end
B=[];old=find(S.ids==env.servingID,1);
if isempty(old)||numel(S.ids)<2||max(S.features(6,:))>=threshold,return;end
alternatives=find(S.ids~=env.servingID);[~,j]=max(S.snr(alternatives));other=alternatives(j);
indices=[old other];beforeTime=env.time;beforeStreak=env.streak;beforeLoss=env.loss;
for branch=1:2
    fork=copy(env);obs=fork.observe();assert(isequal(obs.features,S.features));
    id=S.ids(indices(branch));[next,reward,done]=fork.step(id);
    rows=beforeTime*env.config.packetRate_pps+(1:env.config.packetRate_pps).';
    X=struct('index',indices(branch),'satelliteID',id,'reward',reward,'next',next,'done',done, ...
        'lostCount',sum(fork.loss(rows)),'endStreak',fork.streak,'fork',fork);
    if branch==1,B=struct('state',S,'time_s',beforeTime,'stay',X,'switch',[]);else,B.switch=X;end
end
assert(env.time==beforeTime&&env.streak==beforeStreak&&isequal(env.loss,beforeLoss),'Fork mutated real trajectory');
assert(isequal(B.stay.fork.snr,B.switch.fork.snr)&&isequal(B.stay.fork.draws,B.switch.fork.draws));
end
