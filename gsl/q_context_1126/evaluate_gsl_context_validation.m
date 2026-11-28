function V=evaluate_gsl_context_validation()
% Frozen evaluation on new seeds not used in training or prior burst diagnosis.
here=fileparts(mfilename('fullpath'));modes={'uniform','context'};
roots=cell(1,2);roots{1}=fullfile(fileparts(fileparts(mfilename('fullpath'))),'ddqn_6x11','results_ddqn_6x11','20261123_160855_135');
base=fullfile(here,'results_context');roots{2}=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
S=load(fullfile(roots{1},'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(roots{1},'geometry.mat'),'geometry');G=S.geometry;
seeds=20275001:20275010;assert(isempty(intersect(seeds,[O.trainingSeeds O.evaluationSeeds])));
out=fullfile(here,'validation_new_seeds');if ~isfolder(out),mkdir(out);end
runs=table();allQ=table();
for j=1:2
    S=load(fullfile(roots{j},'agent.mat'),'checkpoint');if j==1,a=GSLTrendDoubleDQN(S.checkpoint.options);else,a=GSLContextDoubleDQN(S.checkpoint.options);end;a.restore(S.checkpoint);
    before=a.updateCount;
    for repeat=1:10
        if j==1,env=GSLTrendEpisode(C,G,O,seeds(repeat));else,env=GSLContextEpisode(C,G,O,seeds(repeat));end;q=zeros(600,1);per=q;ids=q;bestPER=q;bestSNRQ=q;
        for t=0:599
            obs=env.observe();ix=a.select(obs,0,O.qHysteresis);values=double(a.values(obs));
            q(t+1)=values(ix);ids(t+1)=obs.ids(ix);per(t+1)=env.per(t+1,ids(t+1));
            bestPER(t+1)=min(env.per(t+1,obs.ids));[~,ixSNR]=max(obs.snr);bestSNRQ(t+1)=values(ixSNR);
            env.step(ids(t+1));
        end
        [P,M,L]=env.results();
        folder=fullfile(out,sprintf('%s_repeat_%02d',modes{j},repeat));mkdir(folder);
        % Full records allow independent verification, not just aggregate metrics.
        writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));
        writetable(L,fullfile(folder,'decisions.csv'));
        returns=zeros(600,1);g=0;
        for t=600:-1:1,g=env.rewardHistory(t)+O.discountFactor*g;returns(t)=g;end
        trace=table(repmat(string(modes{j}),600,1),repmat(repeat,600,1),(0:599).',ids,per,q, ...
            env.rewardHistory,returns,q-returns,bestPER,bestSNRQ,'VariableNames',{'mode','repeat','time_s','satelliteID','PER', ...
            'predictedQ','reward','realizedDiscountedReturn','QminusRealizedReturn','bestAvailablePER','bestSNR_Q'});
        writetable(trace,fullfile(folder,'Q_return_trace.csv'));allQ=[allQ;trace]; %#ok<AGROW>
        row=table(string(modes{j}),repeat,seeds(repeat),M.generatedPackets,M.receivedPackets,M.lostPackets, ...
            M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(env.handovers), ...
            M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets, ...
            'VariableNames',{'mode','repeat','seed','generated','received','lost','loss_pct','onTime_pct', ...
            'maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','late','pending'});
        runs=[runs;row];writetable(runs,fullfile(out,'runs.csv')); %#ok<AGROW>
        fprintf('NEW SEEDS %s %02d/10 | loss %.4f%% | max %d | HO %d\n',modes{j},repeat,M.packetLossRatio,M.maxConsecutiveLoss,sum(env.handovers));
    end
    assert(a.updateCount==before);
end
writetable(allQ,fullfile(out,'Q_return_traces.csv'));
V=struct('runs',runs,'Q',allQ,'seeds',seeds,'outputDir',out);save(fullfile(out,'validation.mat'),'V','-v7.3');
end
