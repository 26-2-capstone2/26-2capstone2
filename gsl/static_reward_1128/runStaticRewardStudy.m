function R=runStaticRewardStudy(O)
if nargin<1,O=configGSLStaticReward();end
setupStaticReward();assert(isempty(intersect(O.trainingSeeds,O.evaluationSeeds)));
assert(numel(O.trainingSeeds)>=O.numEpisodes&&O.baseConfig.duration_s==600);
out=fullfile(O.resultRoot,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
save(fullfile(out,'options.mat'),'O');runs=table();trainingAll=table();
% Both rewards get identical initial weights, episode seeds, layout/channel/draws.
% Exploration trajectories may diverge after policies diverge; pairing applies to exogenous randomness.
for arm=1:numel(O.rewardDefinitions)
    D=O.rewardDefinitions(arm);agent=GSLTrendDoubleDQN(O);steps=0;training=table();
    initial=agent.checkpoint();save(fullfile(out,[D.name '_initial.mat']),'initial');
    for e=1:O.numEpisodes
        env=createStaticRewardEpisode(O,O.trainingSeeds(e),D);done=false;trainLoss=[];
        while ~done
            S=env.observe();steps=steps+1;
            epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(steps-1)/O.epsilonDecaySteps);
            j=agent.select(S,epsilon,O.trainingQMargin);[next,r,done]=env.step(S.ids(j));
            agent.remember(S,j,r,next,done);
            if mod(steps,O.trainEvery)==0
                v=agent.learn();if isfinite(v),trainLoss(end+1)=v;end %#ok<AGROW>
            end
        end
        edges=diff([false;env.loss;false]);lens=find(edges==-1)-find(edges==1);longest=0;if ~isempty(lens),longest=max(lens);end
        row=table(string(D.name),e,O.trainingSeeds(e),epsilon,100*mean(env.loss),longest,sum(env.handovers),sum(env.studyRewards),mean(trainLoss), ...
            'VariableNames',{'rewardType','episode','seed','epsilon','loss_pct','maxLossRun','handovers','reward','trainingLoss'});
        training=[training;row]; %#ok<AGROW>
        writetable(training,fullfile(out,[D.name '_training.csv']));
        if mod(e,10)==0||e==O.numEpisodes
            checkpoint=agent.checkpoint();save(fullfile(out,sprintf('%s_agent_%04d.mat',D.name,e)),'checkpoint','O','D','-v7.3');
        end
        fprintf('%s TRAIN %d/%d | loss %.3f%% | max %d | HO %d\n',D.name,e,O.numEpisodes,row.loss_pct,longest,row.handovers);
        drawnow;
    end
    trainingAll=[trainingAll;training]; %#ok<AGROW>
    before=agent.updateCount;
    for margin=O.evaluationQMargins
        policy=sprintf('%s_Q%g',D.name,margin);
        for rep=1:numel(O.evaluationSeeds)
            env=createStaticRewardEpisode(O,O.evaluationSeeds(rep),D);
            while env.time<O.baseConfig.duration_s
                S=env.observe();q=agent.values(S);[~,j]=max(q);old=find(S.features(4,:)>0,1);
                if ~isempty(old)&&q(j)<q(old)+margin,j=old;end
                env.step(S.ids(j));
            end
            runs=[runs;saveEval(env,policy,rep,out)]; %#ok<AGROW>
            writetable(runs,fullfile(out,'runs.csv'));drawnow;
        end
    end
    assert(before==agent.updateCount,'Evaluation must not update weights');
end
for rep=1:numel(O.evaluationSeeds)
    env=createStaticRewardEpisode(O,O.evaluationSeeds(rep),O.rewardDefinitions(1));
    while env.time<O.baseConfig.duration_s
        S=env.observe();[~,j]=max(S.snr);old=find(S.features(4,:)>0,1);
        if ~isempty(old)&&S.snr(j)-S.snr(old)<O.maxSNRMargin_dB,j=old;end
        env.step(S.ids(j));
    end
    runs=[runs;saveEval(env,sprintf('MaxSNR_%gdB',O.maxSNRMargin_dB),rep,out)]; %#ok<AGROW>
    if isfield(O,'includeElevation')&&O.includeElevation
        env=createStaticRewardEpisode(O,O.evaluationSeeds(rep),O.rewardDefinitions(1));
        while env.time<O.baseConfig.duration_s
            S=env.observe();[~,j]=max(S.elevation);old=find(S.features(4,:)>0,1);
            if ~isempty(old)&&S.elevation(j)-S.elevation(old)<O.elevationMargin_deg,j=old;end
            env.step(S.ids(j));
        end
        runs=[runs;saveEval(env,sprintf('Elevation_%gdeg',O.elevationMargin_deg),rep,out)]; %#ok<AGROW>
    end
    writetable(runs,fullfile(out,'runs.csv'));drawnow;
end
writetable(runs,fullfile(out,'runs.csv'));summary=table();
for policy=unique(runs.policy,'stable').'
    T=runs(runs.policy==policy,:);
    for metric={'loss_pct','maxLossRun','onTime_pct','handovers'}
        x=T.(metric{1});summary=[summary;table(policy,string(metric{1}),numel(x),mean(x),std(x),min(x),max(x), ...
            'VariableNames',{'policy','metric','n','mean','std','min','max'})]; %#ok<AGROW>
    end
end
writetable(summary,fullfile(out,'summary.csv'));
paired=table();
for margin=O.evaluationQMargins
    a=runs(runs.policy==string(sprintf('linear_Q%g',margin)),:);
    b=runs(runs.policy==string(sprintf('quadratic_Q%g',margin)),:);
    if isempty(a)||isempty(b),continue;end
    assert(isequal(a.seed,b.seed));
    delta=table(a.seed,repmat(margin,height(a),1),b.loss_pct-a.loss_pct,b.maxLossRun-a.maxLossRun,b.onTime_pct-a.onTime_pct,b.handovers-a.handovers, ...
        'VariableNames',{'seed','qMargin','lossDelta_pp','maxRunDelta_packets','onTimeDelta_pp','handoverDelta'});
    paired=[paired;delta]; %#ok<AGROW>
end
if ~isempty(paired),writetable(paired,fullfile(out,'paired_changes.csv'));end
R=struct('options',O,'outputDir',out,'training',trainingAll,'runs',runs,'summary',summary,'pairedChanges',paired);
save(fullfile(out,'study.mat'),'R','-v7.3');
if ~O.smoke,fid=fopen(fullfile(O.resultRoot,'latest_result.txt'),'w');fprintf(fid,'%s',out);fclose(fid);end
if O.makePlots,plotStaticRewardStudy(R);end
disp(summary);fprintf('COMPLETE | %s\n',out);
end
function row=saveEval(env,policy,rep,out)
[P,M,L]=env.results();G=env.geometry;
assert(M.pendingPackets==0&&M.lostPackets==M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets);
assert(M.handoverLossPackets==6*sum(env.handovers));
P.rewardStreak=env.streakSamples;
P.destinationPlaneIndex=G.planeIndex(P.destinationSatelliteID);P.destinationSatelliteInPlane=G.satelliteInPlane(P.destinationSatelliteID);
folder=fullfile(out,policy,sprintf('repeat_%02d',rep));mkdir(folder);
writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));
L.studyReward=[env.studyRewards;NaN];L.onTimeReward=[env.rewardTerms(:,1);NaN];
L.streakCost=[env.rewardTerms(:,2);NaN];L.handoverCost=[env.rewardTerms(:,3);NaN];
writetable(L,fullfile(folder,'decisions.csv'));writetable(G.staticSatellites,fullfile(folder,'satellites.csv'));
seed=G.layout.episodeSeed;snr=env.snr;per=env.per;draws=env.draws;config=env.config;
save(fullfile(folder,'environment.mat'),'G','snr','per','draws','config','-v7');
row=table(string(policy),rep,seed,M.generatedPackets,M.receivedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss, ...
    sum(env.handovers),M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.pendingPackets, ...
    'VariableNames',{'policy','repeat','seed','generated','received','lost','loss_pct','onTime_pct','maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','pending'});
fprintf('EVAL %s repeat %d | loss %.3f%% | max %d | HO %d\n',policy,rep,row.loss_pct,row.maxLossRun,row.handovers);
end
