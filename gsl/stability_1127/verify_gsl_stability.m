function verify_gsl_stability()
gsl=setupGSLStability();O=configGSLStability('control');a=GSLTrendDoubleDQN(O);b=GSLStabilityDoubleDQN(O);
p=fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356');D=load(fullfile(p,'study.mat'),'R');C=configGSLToolboxPHY(D.R.config);D=load(fullfile(p,'geometry.mat'),'geometry');
env=GSLTrendEpisode(C,D.geometry,O,O.trainingSeeds(1));
for t=1:560
    S=env.observe();epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(t-1)/O.epsilonDecaySteps);
    ia=a.select(S,epsilon,O.qHysteresis);ib=b.select(S,epsilon,O.qHysteresis);assert(ia==ib);
    [next,r,done]=env.step(S.ids(ia));a.remember(S,ia,r,next,done);b.remember(S,ib,r,next,done);
    if mod(t,O.trainEvery)==0
        x=a.learn();y=b.learn();assert(isequaln(x,y));
        for j=1:height(a.onlineNetwork.Learnables),assert(isequal(extractdata(a.onlineNetwork.Learnables.Value{j}),extractdata(b.onlineNetwork.Learnables.Value{j})));end
    end
end
% Pure inference must not consume the agent's action/replay stream.
for k=1:20,b.values(S);end
assert(a.select(S,.5,.02)==b.select(S,.5,.02));
T=configGSLStability('soft_target');T.batchSize=4;T.warmupSteps=4;T.replayCapacity=10;
c=GSLStabilityDoubleDQN(T);old=c.targetNetwork;
for k=1:4,c.remember(S,1,k/10,S,false);end
assert(isfinite(c.learn()));
for j=1:height(c.onlineNetwork.Learnables)
    expected=.99*old.Learnables.Value{j}+.01*c.onlineNetwork.Learnables.Value{j};
    assert(isequal(extractdata(expected),extractdata(c.targetNetwork.Learnables.Value{j})));
end
fprintf('STABILITY PASS: instrumented default equals original actions/loss/weights; inference leaves RNG untouched; soft-target blend verified.\n');
end
