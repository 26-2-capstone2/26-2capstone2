function T=compare_stay_switch_training()
% Training seeds only. Change first action once, then same frozen parent policy.
here=fileparts(mfilename('fullpath'));gsl=fileparts(fileparts(mfilename('fullpath')));
base=fullfile(gsl,'q_context_1126','results_context');parent=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
S=load(fullfile(parent,'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(parent,'geometry.mat'),'geometry');G=S.geometry;
S=load(fullfile(parent,'agent.mat'),'checkpoint');a=GSLContextDoubleDQN(O);a.restore(S.checkpoint);before=a.updateCount;
census=readtable(fullfile(gsl,'q_context_1126','training_candidate_context_census.csv'));
seeds=census.seed(census.allCandidatesPER1_seconds+census.bestSuccess0to0_1_seconds>0);
out=fullfile(here,'stay_switch_diagnostics');mkdir(out);T=table();seen=0;skipped=0;
for seed=seeds.'
    env=GSLBranchEpisode(C,G,O,seed);success=1-env.per;success(~G.isVisible)=-Inf;
    times=find(max(success(1:C.duration_s,:),[],2)<.1)-1;last=max(times);
    for t=0:last
        obs=env.observe();
        if ismember(t,times)
            seen=seen+1;B=gslStaySwitchPair(env,obs,.1);
            if isempty(B),skipped=skipped+1;
            else
                stay=roll(B.stay);sw=roll(B.switch);
                row=table(seed,t,env.servingID,B.stay.satelliteID,B.switch.satelliteID,env.streak, ...
                    max(obs.features(6,:)),env.per(t+1,B.stay.satelliteID),env.per(t+1,B.switch.satelliteID), ...
                    B.stay.reward,B.switch.reward,B.stay.lostCount,B.switch.lostCount, ...
                    stay.horizon,stay.ret,sw.ret,sw.ret-stay.ret,stay.lost,sw.lost,stay.maxrun,sw.maxrun, ...
                    'VariableNames',{'seed','time_s','previousID','stayID','switchID','priorStreak','bestSuccess', ...
                    'stayPER','switchPER','stayImmediateReward','switchImmediateReward','stayFirstSecondLost','switchFirstSecondLost', ...
                    'horizon_s','stayDiscountedReturn','switchDiscountedReturn','switchMinusStayReturn','stayWindowLoss', ...
                    'switchWindowLoss','stayWindowMaxRunWithCarry','switchWindowMaxRunWithCarry'});
                T=[T;row];writetable(T,fullfile(out,'pairs.csv')); %#ok<AGROW>
            end
        end
        ix=gslGreedyFrozenChoice(a,obs,O.qHysteresis);id=0;if ix>0,id=obs.ids(ix);end;env.step(id);
    end
    fprintf('PAIR DIAGNOSTIC seed %d | cumulative cases %d | all-poor seen %d | no-stay skipped %d\n',seed,height(T),seen,skipped);
end
assert(seen==95&&height(T)+skipped==seen&&a.updateCount==before);
save(fullfile(out,'diagnostics.mat'),'T','seen','skipped','O','-v7.3');
fprintf('PAIR DIAGNOSTIC COMPLETE: %d eligible pairs, %d no-stay cases, frozen parent, no learning.\n',height(T),skipped);
    function D=roll(branch)
        e=branch.fork;h=min(60,C.duration_s-t);ret=branch.reward;
        for k=1:h-1
            S=e.observe();ix=gslGreedyFrozenChoice(a,S,O.qHysteresis);id=0;if ix>0,id=S.ids(ix);end
            [~,r]=e.step(id);ret=ret+O.discountFactor^k*r;
        end
        rows=t*C.packetRate_pps+(1:h*C.packetRate_pps).';
        D=struct('horizon',h,'ret',ret,'lost',sum(e.loss(rows)),'maxrun',max(e.stepMaxRun(t+1:t+h)));
    end
end
