function verify_gsl_trend_ddqn()
O=configGSLTrendDDQN();C=O.baseConfig;C.duration_s=8;
C.makePlots=false;C.exportResults=false;C.openPacketViewer=false;
G=buildGSLSelectionGeometry(C);env=GSLTrendEpisode(C,G,O,20269993);
for t=0:7
    S=env.observe();assert(size(S.features,1)==11);
    for j=1:numel(S.ids)
        h=S.trendHistory_s(j);id=S.ids(j);
        if h>0
            expected=(env.snr(t+1,id)-env.snr(t+1-h,id))/h;
            assert(abs(expected-S.trend5_dB_per_s(j))<1e-12);
            assert(all(G.isVisible(t+1-h:t+1,id)));
        else,assert(S.trend5_dB_per_s(j)==0);end
    end
    [~,ix]=max(S.snr);env.step(S.ids(ix));
end
[P,M,~]=env.results();assert(height(P)==480 && M.pendingPackets==0);
assert(M.lostPackets==M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets);
% Change future samples only: the state at t=3 must remain identical.
G2=G;G2.slantRange_m(5:end,:)=G2.slantRange_m(5:end,:)*1.01;
a=GSLTrendEpisode(C,G,O,20269993);b=GSLTrendEpisode(C,G2,O,20269993);
for k=1:3
    A=a.observe();B=b.observe();assert(isequal(A.features,B.features));
    id=A.ids(1);a.step(id);b.step(id);
end
A=a.observe();B=b.observe();assert(isequal(A.features,B.features));
O.batchSize=4;O.warmupSteps=4;O.replayCapacity=20;
agent=GSLTrendDoubleDQN(O);
for n=[0 1 13 42 100]
    S=struct('ids',(1:n).','features',zeros(11,n,'single'));
    assert(numel(agent.values(S))==n);
end
for k=1:8
    A=struct('ids',[1;2],'features',single(ones(11,2)*k/10));
    B=struct('ids',(1:mod(k,4)).','features',single(ones(11,mod(k,4))));
    agent.remember(A,1,.2,B,k==8);
end
loss=agent.learn();assert(isfinite(loss) && agent.updateCount==1);
fprintf('TREND DDQN PASS: causal 5s history, no future leakage, packets, variable candidates, gradient\n');
end
