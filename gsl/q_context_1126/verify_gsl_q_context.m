function verify_gsl_q_context()
% Check target math separately from the candidate-state representation.
y=gslContextTargets(single([.2 .3 .4 .5]),[false true false false],[2 1 0 3], ...
    [9 8 99 1 3 2],[2 100 500 4 5 90],.95);
expected=single([.2+.95*2 .3 .4 .5+.95*5]);
assert(isequal(y,expected)); % target-network argmax would give a different result
O=configGSLQContext();a=GSLTrendDoubleDQN(O);b=GSLContextDoubleDQN(O);
for n=[0 1 13 42 100]
    S=struct('ids',(1:n).','features',single(reshape(sin(1:11*n),11,n)));
    B=S;B.features=[S.features;zeros(1,n,'single')];
    assert(max([0 abs(double(a.values(S))-double(b.values(B)))])<2e-6);
end
S=struct('ids',[1;2;3],'features',zeros(11,3,'single'));
L=S;H=S;H.features(6,2)=1;
qL=a.values(L);qH=a.values(H);assert(qL(1)==qH(1));
L.features=[L.features;repmat(max(L.features(6,:)),1,3)];
H.features=[H.features;repmat(max(H.features(6,:)),1,3)];
assert(isequal(L.features(1:11,1),H.features(1:11,1))&&L.features(12,1)~=H.features(12,1));
% Same action trajectory must give identical packet outcomes and rewards.
C=O.baseConfig;C.duration_s=8;C.makePlots=false;C.exportResults=false;C.openPacketViewer=false;
G=buildGSLSelectionGeometry(C);old=GSLTrendEpisode(C,G,O,20279993);new=GSLContextEpisode(C,G,O,20279993);
for t=0:7
    A=old.observe();B=new.observe();assert(isequal(A.features,B.features(1:11,:)));
    assert(all(B.features(12,:)==max(A.features(6,:))));
    id=A.ids(1);[~,r1]=old.step(id);[~,r2]=new.step(id);assert(r1==r2);
end
assert(isequal(old.loss,new.loss));S=new.observe();assert(isequal(size(S.features),[12 0]));
G2=G;G2.slantRange_m(5:end,:)=1.01*G2.slantRange_m(5:end,:);
x=GSLContextEpisode(C,G,O,20279993);z=GSLContextEpisode(C,G2,O,20279993);
for t=1:3,A=x.observe();B=z.observe();assert(isequal(A.features,B.features));x.step(A.ids(1));z.step(B.ids(1));end
A=x.observe();B=z.observe();assert(isequal(A.features,B.features));
% New input participates in gradients and survives variable terminal batches.
O.batchSize=4;O.warmupSteps=4;O.replayCapacity=10;O.targetUpdateEvery=1;b=GSLContextDoubleDQN(O);
for t=1:8
    A=struct('ids',[1;2],'features',single(ones(12,2)*t/10));B=A;
    if mod(t,3)==0,B.ids=zeros(0,1);B.features=zeros(12,0,'single');end
    b.remember(A,1,t/10,B,mod(t,3)==0);
end
assert(isfinite(b.learn())&&b.updateCount==1);
fprintf('Q CONTEXT PASS: DDQN targets, matched initialization, representation gap, unchanged rewards/packets, causal context, gradient.\n');
end
