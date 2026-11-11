function R=train_gsl_ddqn(O)
% Run with F5 for the default budget, or pass configGSLDQN() with edits.
if nargin<1, O=configGSLDQN(); end
validateOptions(O);
assert(exist('dlnetwork','file')~=0,'GSL:DeepLearningToolbox', ...
    'Double DQN requires Deep Learning Toolbox.');
if ~isfolder(O.outputDir), mkdir(O.outputDir); end
env=GSLRLEnvironment(O.rewardWeights);
state=env.observe();
agent=GSLDoubleDQN(numel(state.vector),env.maxCandidateCount,O);
history=table();
steps=0;
for episode=1:O.numEpisodes
    env.reset(O.trainingSeeds(episode));
    state=env.observe();
    done=false; totalReward=0; losses=[]; handovers=0;
    while ~done
        epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)* ...
            max(0,1-steps/O.epsilonDecaySteps);
        action=agent.select(state,epsilon);
        [~,feedback,done]=env.step(action);
        next=env.observe();
        agent.remember(state,action,feedback.reward,next,done);
        steps=steps+1;
        if mod(steps,O.trainEvery)==0
            loss=agent.learn();
            if isfinite(loss), losses(end+1)=loss; end
        end
        totalReward=totalReward+feedback.reward;
        handovers=handovers+feedback.handover;
        state=next;
    end
    [~,M]=env.results();
    meanLoss=NaN;
    if ~isempty(losses), meanLoss=mean(losses); end
    row=table(episode,O.trainingSeeds(episode),epsilon,totalReward,meanLoss, ...
        agent.updateCount,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
        M.maxConsecutiveLoss,handovers,'VariableNames',{'episode','packetSeed', ...
        'epsilon','reward','trainingLoss','gradientUpdates','loss_pct', ...
        'onTime_pct','maxConsecutiveLoss','handovers'});
    history=[history;row];
    fprintf('Episode %d/%d | reward %.2f | loss %.3f%% | on time %.3f%% | max run %d | epsilon %.3f | updates %d\n', ...
        episode,O.numEpisodes,totalReward,M.packetLossRatio, ...
        M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,epsilon,agent.updateCount);
    writetable(history,fullfile(O.outputDir,'training_history.csv'));
    saveCheckpoint(agent,O,history);
end
comparison=evaluate_gsl_ddqn(agent,O,env);
if O.makePlots
    f=figure('Name','GSL Double DQN training');
    tiledlayout(2,1);
    nexttile; plot(history.episode,history.reward); xlabel('Episode'); ylabel('Training reward');
    nexttile; plot(history.episode,history.maxConsecutiveLoss); xlabel('Episode'); ylabel('Maximum loss run');
    exportgraphics(f,fullfile(O.outputDir,'training.png'));
    f=figure('Name','GSL policy comparison');
    names=["existing";"max_snr";"double_dqn"];
    values=zeros(3,3);
    for k=1:3
        rows=comparison.policy==names(k);
        values(k,:)=[mean(comparison.loss_pct(rows)),mean(comparison.onTime_pct(rows)), ...
            mean(comparison.maxConsecutiveLoss(rows))];
    end
    tiledlayout(1,3);
    labels={'Loss [%]','On-time [%]','Maximum loss run [packets]'};
    for k=1:3
        nexttile; bar(values(:,k)); xticks(1:3); xticklabels(names);
        ylabel(labels{k}); title('Mean across evaluation seeds');
    end
    exportgraphics(f,fullfile(O.outputDir,'comparison.png'));
end
R=struct('agent',agent,'history',history,'comparison',comparison,'options',O);
fprintf('Saved training and held-out evaluation to %s\n',O.outputDir);
end

function validateOptions(O)
for name={'numEpisodes','batchSize','replayCapacity','warmupSteps', ...
        'trainEvery','targetUpdateEvery','epsilonDecaySteps'}
    validateattributes(O.(name{1}),{'numeric'},{'scalar','integer','positive','finite'});
end
validateattributes(O.learningRate,{'numeric'},{'scalar','positive','finite'});
validateattributes(O.gradientThreshold,{'numeric'},{'scalar','positive','finite'});
validateattributes(O.discountFactor,{'numeric'},{'scalar','>=',0,'<=',1,'finite'});
validateattributes(O.epsilonStart,{'numeric'},{'scalar','>=',0,'<=',1,'finite'});
validateattributes(O.epsilonEnd,{'numeric'},{'scalar','>=',0,'<=',O.epsilonStart,'finite'});
validateattributes(O.trainingSeeds,{'numeric'},{'vector','integer','nonnegative','finite','<=',2^32-1});
validateattributes(O.evaluationSeeds,{'numeric'},{'vector','nonempty','integer','nonnegative','finite','<=',2^32-1});
assert(numel(O.trainingSeeds)>=O.numEpisodes,'GSL:DQNTrainingSeeds');
assert(isempty(intersect(O.trainingSeeds(1:O.numEpisodes),O.evaluationSeeds)), ...
    'GSL:DQNSeedOverlap','Evaluation seeds must be excluded from training.');
assert(O.replayCapacity>=max(O.batchSize,O.warmupSteps),'GSL:DQNReplaySize');
end

function saveCheckpoint(agent,O,history)
temporary=fullfile(O.outputDir,'agent_pending.mat');
save(temporary,'agent','O','history','-v7.3');
[ok,message]=movefile(temporary,fullfile(O.outputDir,'agent.mat'),'f');
assert(ok,'GSL:DQNCheckpoint','%s',message);
end
