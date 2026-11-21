function [agent,training]=train_gsl_three_ddqn(O,geometries,configs,out)
agent=GSLCandidateDoubleDQN(O); training=table(); steps=0;
for e=1:O.numEpisodes
    k=mod(e-1,3)+1; env=GSLSelectionEpisode(configs{k},geometries{k},O,O.trainingSeeds(e));
    losses=[]; done=false;
    while ~done
        S=env.observe(); steps=steps+1;
        epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(steps-1)/O.epsilonDecaySteps);
        index=agent.select(S,epsilon,O.qHysteresis); id=0;if index>0,id=S.ids(index);end
        [next,reward,done]=env.step(id);
        agent.remember(S,index,reward,next,done);
        if mod(steps,O.trainEvery)==0
            loss=agent.learn();if isfinite(loss),losses(end+1)=loss;end %#ok<AGROW>
        end
    end
    edges=diff([false;env.loss;false]); lengths=find(edges==-1)-find(edges==1);
    maxRun=0;if ~isempty(lengths),maxRun=max(lengths);end
    meanLoss=NaN;if ~isempty(losses),meanLoss=mean(losses);end
    row=table(e,O.sizes(k,1),O.sizes(k,2),O.trainingSeeds(e),epsilon, ...
        100*mean(env.loss),maxRun,sum(env.handovers),sum(env.rewardHistory),meanLoss,agent.updateCount, ...
        'VariableNames',{'episode','planes','satellitesPerPlane','seed','epsilon','loss_pct', ...
        'maxLossRun','handovers','reward','trainingLoss','updates'});
    training=[training;row]; %#ok<AGROW>
    writetable(training,fullfile(out,'training.csv'));
    fprintf('TRAIN %d/%d | %dx%d | loss %.3f%% | max run %d | HO %d | eps %.3f | updates %d\n', ...
        e,O.numEpisodes,O.sizes(k,1),O.sizes(k,2),row.loss_pct,maxRun,row.handovers,epsilon,agent.updateCount);
    checkpoint=agent.checkpoint(); %#ok<NASGU>
    save(fullfile(out,'agent.mat'),'checkpoint','O','-v7.3');
end
end
