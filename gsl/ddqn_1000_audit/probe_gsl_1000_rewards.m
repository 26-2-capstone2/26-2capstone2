function T=probe_gsl_1000_rewards(ddqnRoot,oldRoot,out)
% Counterfactual one-second reward calculations at the exact saved state.
S=load(fullfile(ddqnRoot,'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(ddqnRoot,'geometry.mat'),'geometry');G=S.geometry;
S=load(fullfile(ddqnRoot,'agent.mat'),'checkpoint');a=GSLTrendDoubleDQN(O);a.restore(S.checkpoint);
S=load(fullfile(oldRoot,'agent.mat'),'checkpoint');b=GSLTrendDoubleDQN(O);b.restore(S.checkpoint);
T=table();
for repeat=[7 10]
    S=load(fullfile(ddqnRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');P=S.preview;
    env=GSLTrendEpisode(C,G,O,P.seed);
    for t=0:599
        obs=env.observe();q=double(a.values(obs));q100=double(b.values(obs));
        ix=a.select(obs,0,O.qHysteresis);id=obs.ids(ix);
        assert(id==P.L.servingSatID(t+1));
        if (repeat==7 && ismember(t,2:7)) || (repeat==10 && ismember(t,18:24))
            n=numel(obs.ids);expected=zeros(n,1);actual=expected;ho=false(n,1);cost=expected;on=expected;
            for j=1:n
                [expected(j),actual(j),ho(j),cost(j),on(j)]=rewardFor(obs.ids(j));
            end
            [~,bestSNR]=max(obs.snr);[~,bestImmediate]=max(expected);[~,bestOldQ]=max(q100);
            row=table(repmat(repeat,n,1),repmat(t,n,1),obs.ids,obs.snr, ...
                env.per(t+1,obs.ids).',q.',q100.',expected,actual,on,cost,ho, ...
                repmat(env.streak,n,1),obs.ids==id,(1:n).'==bestSNR,(1:n).'==bestImmediate,(1:n).'==bestOldQ, ...
                'VariableNames',{'repeat','time_s','satelliteID','SNR_dB','PER','Q1000','Q100_same_state', ...
                'expectedImmediateReward','sameDrawImmediateReward','expectedOnTimeFraction', ...
                'expectedBurstCost','handover','priorStreak','chosen','bestSNR','bestImmediateReward','bestQ100'});
            T=[T;row]; %#ok<AGROW>
            chosenExpected=expected(ix);snrExpected=expected(bestSNR);
            fprintf('PROBE repeat=%d t=%d chosen=%d Q=%.5f PER=%.5f Ereward=%.5f | bestSNR=%d Q=%.5f PER=%.5f Ereward=%.5f\n', ...
                repeat,t,id,q(ix),env.per(t+1,id),chosenExpected,obs.ids(bestSNR),q(bestSNR),env.per(t+1,obs.ids(bestSNR)),snrExpected);
            [~,r]=env.step(id);assert(abs(r-actual(ix))<1e-10,'Reward formula mismatch');
        else
            env.step(id);
        end
    end
    assert(isequal(env.loss,logical(P.P.lost)));
end
writetable(T,fullfile(out,'focused_candidate_rewards.csv'));
fprintf('REWARD PROBE PASS: chosen reward exactly matches environment; expected reward uses current PER, no future channel.\n');
    function [er,ar,h,ec,eo]=rewardFor(sat)
        N=C.packetRate_pps;h=env.servingID>0 && sat~=env.servingID;
        u=(0:N-1).'/N;blocked=h & u<C.handoverInterruption_s-16*eps(max(1,t+1));
        p=env.per(t+1,sat);ps=repmat(p,N,1);ps(blocked)=1;
        latency=G.slantRange_m(t+1,sat)/299792458+gslPacketInformationBits(C)/C.linkDataRate_bps+C.receiverProcessing_s;
        deadlineOK=latency<=C.gslDeadline_s;
        eo=mean(1-ps)*deadlineOK;
        % Distribution of capped streak gives exact expected bounded cost.
        cap=10*N;dist=zeros(cap+1,1);dist(min(env.streak,cap)+1)=1;cs=zeros(N,1);
        for z=1:N
            next=zeros(cap+1,1);next(1)=1-ps(z);
            next(2:end)=ps(z)*dist(1:end-1);next(end)=next(end)+ps(z)*dist(end);
            dist=next;cs(z)=sum((0:cap).'.*dist)/N;
        end
        ec=mean(cs);w=O.rewardWeights;er=w.onTime*eo-w.burst*ec-w.handover*h;
        rows=t*N+(1:N).';lost=blocked|env.draws(rows)<p;s=env.streak;cs=zeros(N,1);
        for z=1:N,if lost(z),s=s+1;else,s=0;end;cs(z)=min(s/N,10);end
        ar=w.onTime*mean(~lost)*deadlineOK-w.burst*mean(cs)-w.handover*h;
    end
end
