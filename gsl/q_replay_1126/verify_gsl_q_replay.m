function verify_gsl_q_replay()
O=configGSLTrendDDQN();O.batchSize=4;O.warmupSteps=4;O.replayCapacity=8;
O.replayMode='uniform';O.priorityAlpha=.6;O.priorityEpsilon=1e-5;O.priorityBetaStart=.4;O.priorityBetaUpdates=50;
a=GSLTrendDoubleDQN(O);b=GSLReplayDoubleDQN(O);
for t=1:30
    x=single(reshape(sin((1:33)+t),11,3));x(6,:)=[.99 .5 .01];
    S=struct('ids',(1:3).','features',x);next=S;if mod(t,5)==0,next.ids=zeros(0,1);next.features=zeros(11,0,'single');end
    ia=a.select(S,.2,.02);ib=b.select(S,.2,.02);assert(ia==ib);
    a.remember(S,ia,t/100,next,mod(t,5)==0);b.remember(S,ib,t/100,next,mod(t,5)==0);
    la=a.learn();lb=b.learn();assert(isequaln(la,lb));assert(isequal(a.values(S),b.values(S)));
end
assert(b.replaySnapshot().count==8); % wrapped buffer exercised
O.replayMode='prioritized';c=GSLReplayDoubleDQN(O);
for t=1:50
    S=struct('ids',[1;2],'features',single(ones(11,2)*t/100));
    S.features(6,:)=[1 0];next=S;terminal=mod(t,3)==0;
    if terminal,next.ids=zeros(0,1);next.features=zeros(11,0,'single');end
    c.remember(S,1+mod(t,2),double(mod(t,5)==0)*3,next,terminal);c.learn();
end
D=c.replaySnapshot();assert(all(isfinite(D.priorities))&&all(D.priorities>0));
assert(height(c.learningDiagnostics)>0 && sum(c.seenCounts)==50);
assert(all(c.learningDiagnostics.minISweight>0)&&all(c.learningDiagnostics.maxISweight<=1+eps));
assert(sum(c.sampledCounts)==height(c.learningDiagnostics)*O.batchSize);
fprintf('Q REPLAY PASS: uniform branch exactly equals original; prioritized gradient/weights/priorities, terminal and buffer wrap verified.\n');
end
