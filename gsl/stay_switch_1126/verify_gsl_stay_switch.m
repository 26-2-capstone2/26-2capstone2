function verify_gsl_stay_switch()
O=configGSLStaySwitch();C=O.baseConfig;C.duration_s=8;C.makePlots=false;
G=buildGSLSelectionGeometry(C);a=GSLBranchEpisode(C,G,O,20279992);
S=a.observe();a.step(S.ids(1));a.step(a.observe().ids(1));
before=a.observe();x=copy(a);z=copy(a);
assert(isequal(x.observe().features,before.features));
id=before.ids(1);[~,r]=x.step(id);
assert(a.time==2&&z.time==2&&x.time==3);
[~,rz]=z.step(id);assert(r==rz&&isequal(x.loss,z.loss));
% Eligibility can be widened for this mechanical test, never in the experiment.
B=gslStaySwitchPair(a,before,1.01);assert(~isempty(B));
assert(B.stay.satelliteID==a.servingID&&B.switch.satelliteID~=a.servingID);
assert(a.time==2&&B.stay.fork.time==3&&B.switch.fork.time==3);
q=GSLContextDoubleDQN(O);ix=gslGreedyFrozenChoice(q,before,O.qHysteresis);
assert(ix>=1&&ix<=numel(before.ids));
O.batchSize=4;O.warmupSteps=4;O.replayCapacity=10;O.rareReplayCapacity=10;O.rareBatchQuota=2;O.targetUpdateEvery=1;
u=GSLContextDoubleDQN(O);v=GSLPairedDoubleDQN(O);
for k=1:20
    A=struct('ids',[1;2],'features',single(reshape(sin((1:24)+k),12,2)));D=A;
    if mod(k,4)==0,D.ids=zeros(0,1);D.features=zeros(12,0,'single');end
    iu=u.select(A,.2,.02);iv=v.select(A,.2,.02);assert(iu==iv);
    u.remember(A,iu,k/100,D,mod(k,4)==0);v.remember(A,iv,k/100,D,mod(k,4)==0);
    lu=u.learn();lv=v.learn();assert(isequaln(lu,lv)&&isequal(u.values(A),v.values(A)));
end
p=GSLPairedDoubleDQN(O);
for k=1:8
    p.remember(before,B.stay.index,B.stay.reward,B.stay.next,B.stay.done);
end
p.rememberRare(before,B.stay.index,B.stay.reward,B.stay.next,B.stay.done);
p.rememberRare(before,B.switch.index,B.switch.reward,B.switch.next,B.switch.done);
assert(isfinite(p.learn())&&p.updateCount==1);
assert(p.lastRareBatchCount==2&&p.rareCount==2);
fprintf('STAY/SWITCH PASS: independent exact forks, unchanged original, matched random draws, separate replay and gradient.\n');
end
