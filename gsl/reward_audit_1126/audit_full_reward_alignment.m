function R=audit_full_reward_alignment()
here=fileparts(mfilename('fullpath'));gsl=fileparts(fileparts(mfilename('fullpath')));
parent=fullfile(gsl,'q_context_1126','results_context','20261126_003447_332');
S=load(fullfile(parent,'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(parent,'geometry.mat'),'geometry');G=S.geometry;
S=load(fullfile(parent,'agent.mat'),'checkpoint');agent=GSLContextDoubleDQN(O);agent.restore(S.checkpoint);updates=agent.updateCount;
old=readtable(fullfile(gsl,'stay_switch_1126','stay_switch_diagnostics','pairs.csv'));
out=fullfile(here,'full_episode_audit');mkdir(out);pairs=table();scores=table();trace=table();
for seed=unique(old.seed).'
    rows=find(old.seed==seed);snapshots=cell(numel(rows),1);
    ref=GSLBranchEpisode(C,G,O,seed);beforeStreak=zeros(C.duration_s+1,1);
    for t=0:C.duration_s-1
        beforeStreak(t+1)=ref.streak;local=find(old.time_s(rows)==t,1);
        if ~isempty(local),snapshots{local}=copy(ref);end
        obs=ref.observe();ix=gslGreedyFrozenChoice(agent,obs,O.qHysteresis);id=0;if ix>0,id=obs.ids(ix);end;ref.step(id);
    end
    beforeStreak(end)=ref.streak;
    for local=1:numel(rows)
        k=rows(local);t0=old.time_s(k);env=snapshots{local};S0=env.observe();B=gslStaySwitchPair(env,S0,.1);
        assert(~isempty(B)&&B.stay.satelliteID==old.stayID(k)&&B.switch.satelliteID==old.switchID(k));
        D=cell(1,2);merged=zeros(1,2);
        for branch=1:2
            e=B.stay.fork;if branch==2,e=B.switch.fork;end
            while e.time<C.duration_s
                if e.servingID==ref.selected(e.time)&&e.streak==beforeStreak(e.time+1),break;end
                obs=e.observe();ix=gslGreedyFrozenChoice(agent,obs,O.qHysteresis);id=0;if ix>0,id=obs.ids(ix);end;e.step(id);
            end
            merged(branch)=e.time;n=e.time;packetEnd=n*C.packetRate_pps;
            loss=[e.loss(1:packetEnd);ref.loss(packetEnd+1:end)];
            selected=[e.selected(1:n);ref.selected(n+1:end)];
            ho=[e.handovers(1:n);ref.handovers(n+1:end)];
            reward=[e.rewardHistory(1:n);ref.rewardHistory(n+1:end)];
            D{branch}=reward_components(loss,selected,ho,C,G,O,reward);
            mode="stay";if branch==2,mode="switch";end
            part=table(repmat(seed,600,1),repmat(t0,600,1),repmat(mode,600,1),(0:599).', ...
                D{branch}.success,D{branch}.burstPenalty,D{branch}.handoverPenalty,D{branch}.reward, ...
                'VariableNames',{'seed','decision_s','branch','time_s','successTerm','burstPenalty','handoverPenalty','reward'});
            trace=[trace;part]; %#ok<AGROW>
        end
        a=D{1};b=D{2};future=(t0+1):600;discount=O.discountFactor.^(0:numel(future)-1).';
        h=old.horizon_s(k);w=(t0+1):(t0+h);dw=O.discountFactor.^(0:h-1).';
        assert(abs(sum(dw.*a.reward(w))-old.stayDiscountedReturn(k))<1e-8);
        assert(abs(sum(dw.*b.reward(w))-old.switchDiscountedReturn(k))<1e-8);
        ret=[sum(discount.*a.reward(future)),sum(discount.*b.reward(future))];
        dSuccess=sum(discount.*(b.success(future)-a.success(future)));
        dBurst=-sum(discount.*(b.burstPenalty(future)-a.burstPenalty(future)));
        dHO=-sum(discount.*(b.handoverPenalty(future)-a.handoverPenalty(future)));
        assert(abs((ret(2)-ret(1))-(dSuccess+dBurst+dHO))<1e-9);
        row=table(seed,t0,a.lost,b.lost,a.maxRun,b.maxRun,a.handovers,b.handovers,ret(1),ret(2), ...
            ret(2)-ret(1),dSuccess,dBurst,dHO,merged(1),merged(2), ...
            'VariableNames',{'seed','time_s','stayFullLoss','switchFullLoss','stayFullMaxRun','switchFullMaxRun', ...
            'stayHO','switchHO','stayReturn','switchReturn','switchMinusStayReturn','successContribution', ...
            'burstContribution','HOContribution','stayMergedBy_s','switchMergedBy_s'});
        pairs=[pairs;row]; %#ok<AGROW>
        % Rescore SAME trajectories; this does not evaluate a retrained policy.
        names=["original" "no_extra_HO" "no_discount" "no_extra_HO_no_discount" "onTime_only_no_discount" "burst_only_no_discount" "no_burst"];
        for m=1:numel(names)
            weight=discount;successWeight=1;burstWeight=1;hoWeight=1;
            switch names(m)
                case "no_extra_HO",hoWeight=0;
                case "no_discount",weight=ones(size(discount));
                case "no_extra_HO_no_discount",weight=ones(size(discount));hoWeight=0;
                case "onTime_only_no_discount",weight=ones(size(discount));burstWeight=0;hoWeight=0;
                case "burst_only_no_discount",weight=ones(size(discount));successWeight=0;hoWeight=0;
                case "no_burst",burstWeight=0;
            end
            value=zeros(1,2);
            for branch=1:2,x=D{branch};value(branch)=sum(weight.*(successWeight*x.success(future)-burstWeight*x.burstPenalty(future)-hoWeight*x.handoverPenalty(future)));end
            scores=[scores;table(seed,t0,names(m),value(1),value(2),value(2)-value(1), ...
                'VariableNames',{'seed','time_s','scoring','stay','switch','switchMinusStay'})]; %#ok<AGROW>
        end
    end
    writetable(pairs,fullfile(out,'full_episode_pairs.csv'));writetable(scores,fullfile(out,'fixed_trajectory_rescoring.csv'));
    fprintf('REWARD AUDIT seed %d | %d/92 pairs | full 600s | components and old-window replay PASS\n',seed,height(pairs));
end
assert(height(pairs)==92&&agent.updateCount==updates);
writetable(trace,fullfile(out,'component_traces.csv'));R=struct('pairs',pairs,'scores',scores,'options',O,'outputDir',out);
save(fullfile(out,'audit.mat'),'R','-v7.3');
fprintf('FULL REWARD ALIGNMENT AUDIT COMPLETE: 92 pairs, no training or reward modifications.\n');
end
