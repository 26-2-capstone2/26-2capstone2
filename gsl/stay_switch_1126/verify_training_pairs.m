function verify_training_pairs(out)
S=load(fullfile(out,'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(out,'geometry.mat'),'geometry');G=S.geometry;
T=readtable(fullfile(out,'training_pairs.csv'));assert(all(T.bestSuccess<.1)&&all(T.stayID~=T.switchID));
for seed=unique(T.seed).'
    e=GSLBranchEpisode(C,G,O,seed);rows=find(T.seed==seed);
    for k=rows.'
        t=T.time_s(k);visible=find(G.isVisible(t+1,:));other=visible(visible~=T.stayID(k));
        assert(ismember(T.stayID(k),visible)&&ismember(T.switchID(k),other));
        assert(e.snr(t+1,T.switchID(k))>=max(e.snr(t+1,other))-1e-12);
        for j=1:2
            id=T.stayID(k);h=false;
            if j==2,id=T.switchID(k);h=true;end
            u=(0:59).'/60;ix=t*60+(1:60).';
            lost=(h & u<C.handoverInterruption_s-16*eps(max(1,t+1))) | e.draws(ix)<e.per(t+1,id);
            latency=G.slantRange_m(t+1,id)/299792458+gslPacketInformationBits(C)/C.linkDataRate_bps+C.receiverProcessing_s;
            streak=T.priorStreak(k);cost=zeros(60,1);
            for n=1:60,if lost(n),streak=streak+1;else,streak=0;end;cost(n)=min(streak/60,10);end
            w=O.rewardWeights;r=w.onTime*mean(~lost)*(latency<=C.gslDeadline_s)-w.burst*mean(cost)-w.handover*h;
            if j==1,assert(sum(lost)==T.stayLost(k)&&abs(r-T.stayReward(k))<1e-10);
            else,assert(sum(lost)==T.switchLost(k)&&abs(r-T.switchReward(k))<1e-10);end
        end
    end
end
fprintf('TRAINING PAIRS PASS: %d pairs independently verified from PHY, shared draws, handover and original reward.\n',height(T));
end
