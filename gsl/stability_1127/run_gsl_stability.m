function runs=run_gsl_stability(mode)
gsl=setupGSLStability();O=configGSLStability(mode);out=O.resultRoot;if ~isfolder(out),mkdir(out);end
source=fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356');D=load(fullfile(source,'study.mat'),'R');C=configGSLToolboxPHY(D.R.config);
D=load(fullfile(source,'geometry.mat'),'geometry');G=D.geometry;
D=load(fullfile(gsl,'checkpoint_audit_1127/results/reference_states.mat'),'referenceStates');probe=D.referenceStates{2,2};
probeStay=find(probe.ids==44);probeBad=find(probe.ids==64);assert(~isempty(probeStay)&&~isempty(probeBad));
agent=GSLStabilityDoubleDQN(O);training=table();diagnostics=zeros(0,11);steps=0;runs=table();
geometry=G;save(fullfile(out,'geometry.mat'),'geometry','-v7');save(fullfile(out,'options.mat'),'O','C');
for e=1:200
    env=GSLTrendEpisode(C,G,O,O.trainingSeeds(e));done=false;losses=[];
    while ~done
        S=env.observe();steps=steps+1;epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(steps-1)/O.epsilonDecaySteps);
        ix=agent.select(S,epsilon,O.qHysteresis);id=0;if ix>0,id=S.ids(ix);end
        [next,r,done]=env.step(id);agent.remember(S,ix,r,next,done);
        if mod(steps,O.trainEvery)==0
            loss=agent.learn();if isfinite(loss),losses(end+1)=loss;end %#ok<AGROW>
            if isfinite(loss)&&mod(agent.updateCount,100)==0
                q=agent.values(probe);diagnostics(end+1,:)=[steps e agent.lastDiagnostics q(probeBad)-q(probeStay)]; %#ok<AGROW>
            end
        end
    end
    loss=NaN;if ~isempty(losses),loss=mean(losses);end
    training=[training;table(e,O.trainingSeeds(e),epsilon,100*mean(env.loss),maxRun(env.loss),sum(env.handovers),sum(env.rewardHistory),loss,agent.updateCount, ...
        'VariableNames',{'episode','seed','epsilon','loss_pct','maxLossRun','handovers','reward','trainingLoss','updates'})]; %#ok<AGROW>
    writetable(training,fullfile(out,'training.csv'));
    T=array2table(diagnostics,'VariableNames',{'environmentSteps','episode','updates','trainingLoss','gradientNorm','clipScale','onlineTargetGap','meanReplayAge_steps','sampleBestSuccessUnder20pct','bufferBestSuccessUnder20pct','probeQbadMinusStay'});
    writetable(T,fullfile(out,'learning_diagnostics.csv'));
    fprintf('%s TRAIN %03d/200 | loss %.3f%% | max %d | updates %d\n',mode,e,100*mean(env.loss),maxRun(env.loss),agent.updateCount);
    if mod(e,100)==0
        checkpoint=agent.checkpoint();save(fullfile(out,sprintf('agent_episode_%04d.mat',e)),'checkpoint','O','-v7.3');
        batch=evaluate(agent,O,C,G,e,out);runs=[runs;batch];writetable(runs,fullfile(out,'runs.csv')); %#ok<AGROW>
    end
end
save(fullfile(out,'study.mat'),'runs','training','O','C','-v7.3');
fprintf('%s COMPLETE: 200 episodes, frozen evaluations at 100/200.\n',mode);
end
function runs=evaluate(agent,O,C,G,episode,out)
before=agent.updateCount;runs=table();
for repeat=1:10
    seed=O.evaluationSeeds(repeat);env=GSLTrendEpisode(C,G,O,seed);
    for t=1:600
        S=env.observe();id=0;
        if ~isempty(S.ids)
            q=agent.values(S);[~,ix]=max(q);old=find(S.features(4,:)>0,1);
            if ~isempty(old)&&q(ix)<q(old)+O.qHysteresis,ix=old;end
            id=S.ids(ix);
        end
        env.step(id);
    end
    [P,M,L]=env.results();folder=fullfile(out,sprintf('episode_%04d_repeat_%02d',episode,repeat));mkdir(folder);
    writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));writetable(L,fullfile(folder,'decisions.csv'));
    preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',O.mode,'seed',seed);save(fullfile(folder,'preview.mat'),'preview','-v7.3');
    row=table(string(O.mode),episode,repeat,seed,M.generatedPackets,M.receivedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(env.handovers),M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets,sum(env.rewardHistory), ...
        'VariableNames',{'mode','episode','repeat','seed','generated','received','lost','loss_pct','onTime_pct','maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','late','pending','undiscountedReward'});
    runs=[runs;row]; %#ok<AGROW>
    fprintf('%s EVAL %d %02d/10 | loss %.4f%% | max %d | HO %d\n',O.mode,episode,repeat,M.packetLossRatio,M.maxConsecutiveLoss,sum(env.handovers));
end
assert(agent.updateCount==before);
end
function m=maxRun(lost)
e=diff([false;logical(lost(:));false]);v=find(e==-1)-find(e==1);m=0;if ~isempty(v),m=max(v);end
end
