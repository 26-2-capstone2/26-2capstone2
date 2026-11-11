function verify_gsl_ddqn()
% Regression tests that distinguish Double DQN from max-target DQN.
online=single([5 100 9; 4 7 8; 999 8 7]);
target=single([2 11 4; 90 3 5; 1000 20 6]);
mask=logical([1 0 0;1 1 0;0 1 0]);
y=gslDDQNTargets([1 2 3],[false false true],online,target,mask,0.9);
assert(max(abs(double(y)-[2.8 20 3]))<1e-5);
% All-false mask is the forced no-candidate action in slot 1.
y=gslDDQNTargets(1,false,online(:,1),target(:,1),false(3,1),0.9);
assert(abs(double(y)-2.8)<1e-5);

O=configGSLDQN();
O.warmupSteps=2; O.batchSize=2; O.replayCapacity=4; O.targetUpdateEvery=2;
saved=rng;
agent=GSLDoubleDQN(79,3,O);
assert(isequal(saved,rng),'GSL:DQNRNGIsolation');
state=struct('vector',zeros(79,1),'actionMask',logical([1;0;1]));
for k=1:20
    assert(ismember(agent.select(state,1),[1 3]));
end
assert(ismember(agent.select(state,0),[1 3]));
next=state; next.vector(1)=0.5;
agent.remember(state,1,1,next,false);
assert(isnan(agent.learn()) && agent.updateCount==0);
agent.remember(next,3,-0.2,state,true);
original=agent.onlineNetwork.Learnables;
originalTarget=agent.targetNetwork.Learnables;
assert(isfinite(agent.learn()) && agent.updateCount==1);
assert(~sameWeights(original,agent.onlineNetwork.Learnables));
assert(sameWeights(originalTarget,agent.targetNetwork.Learnables));
assert(isfinite(agent.learn()) && agent.updateCount==2);
assert(sameWeights(agent.onlineNetwork.Learnables,agent.targetNetwork.Learnables));
for k=1:6
    agent.remember(state,1,0.2,next,false);
end
assert(isfinite(agent.learn()));
state.actionMask(:)=false;
assert(agent.select(state,0)==0);
agent.remember(state,0,0,next,false);
fprintf('PASS Double DQN: online selection/target evaluation, masks, terminal target, replay wrap, gradient update, target sync, RNG isolation.\n');
end

function yes=sameWeights(a,b)
yes=true;
for k=1:height(a)
    yes=yes && isequal(extractdata(a.Value{k}),extractdata(b.Value{k}));
end
end
