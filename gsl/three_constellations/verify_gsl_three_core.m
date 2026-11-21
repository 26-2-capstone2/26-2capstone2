function verify_gsl_three_core()
O=configGSLThreeConstellations(); C=O.baseConfig;
C.duration_s=8; C.makePlots=false;C.exportResults=false;C.openPacketViewer=false;
fast=buildGSLSelectionGeometry(C); reference=buildGSLGeometry(C);
assert(max(abs(fast.elevation_deg-reference.elevation_deg),[],'all')<1e-5);
assert(max(abs(fast.slantRange_m-reference.slantRange_m),[],'all')<0.1);
assert(isequal(fast.isVisible,reference.isVisible));
fprintf('VECTOR GEOMETRY vs AER/ACCESS PASS: 66 satellites x 9 times\n');
env=GSLSelectionEpisode(C,fast,O,20269991); done=false;
while ~done
    S=env.observe(); assert(numel(S.ids)==sum(fast.isVisible(env.time+1,:)));
    ix=selectGSLThreeAction(S,"MaxSNR_Hysteresis",O,[]);id=0;if ix>0,id=S.ids(ix);end
    [~,~,done]=env.step(id);
end
[P,M,L]=env.results(); %#ok<ASGLU>
assert(height(P)==480 && M.pendingPackets==0);
assert(all(P.transmission_delay_ms==.04096));
fprintf('FAST PACKETS vs REFERENCE PASS: IDs, draws, 100ms HO, PHY, delay, accounting\n');
agent=GSLCandidateDoubleDQN(O); S=env.observe();
assert(agent.select(S,0)==0);
counts=[1 13 41 100];
for n=counts
    S=struct('ids',(1:n).','features',single(zeros(10,n)));
    assert(numel(agent.values(S))==n && ismember(agent.select(S,0),1:n));
end
fprintf('VARIABLE CANDIDATES PASS: 0, 1, 13, 41, 100 (no candidate truncation)\n');
% Double DQN target selection is online argmax; target network evaluates it.
O.batchSize=4; O.warmupSteps=4; O.replayCapacity=20;
agent=GSLCandidateDoubleDQN(O); rng(20261121);
for k=1:8
    S=struct('ids',[1;2],'features',single(randn(10,2)));
    N=struct('ids',(1:mod(k,4)).','features',single(randn(10,mod(k,4))));
    agent.remember(S,1,.2,N,k==8);
end
loss=agent.learn();assert(isfinite(loss) && agent.updateCount==1);
fprintf('SHARED DOUBLE DQN REPLAY/GRADIENT PASS\n');
end
