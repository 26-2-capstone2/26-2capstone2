function comparison=evaluate_gsl_ddqn(agent,O,env)
% Frozen-policy evaluation. Same original packet draws for each policy/seed.
if nargin<3, env=GSLRLEnvironment(O.rewardWeights); end
if ~isfolder(O.outputDir), mkdir(O.outputDir); end
names=["existing","max_snr","double_dqn"];
cfg=configGSL();
comparison=table();
for seedIndex=1:numel(O.evaluationSeeds)
    seed=O.evaluationSeeds(seedIndex);
    for policy=names
        T=env.reset(seed);
        state=env.observe();
        done=false; reward=0; handovers=0;
        while ~done
            action=0;
            if policy=="double_dqn"
                action=agent.select(state,0);
            elseif ~isempty(T)
                action=1;
                if policy=="existing"
                    [~,order]=sortrows([-T.elevation_deg,T.satelliteID],[1,2]);
                    best=order(1);
                    old=find(T.isServing,1);
                    action=best;
                    if ~isempty(old) && T.elevation_deg(best)<= ...
                            T.elevation_deg(old)+cfg.handoverMargin_deg
                        action=old;
                    end
                end
            end
            [T,feedback,done]=env.step(action);
            state=env.observe();
            reward=reward+feedback.reward;
            handovers=handovers+feedback.handover;
        end
        [P,M]=env.results();
        primary=100*(M.generatedPackets-M.receivedPackets)/M.generatedPackets;
        causes=100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets;
        assert(M.pendingPackets==0 && abs(primary-causes)<1e-10,'GSL:DQNEvaluationAccounting');
        row=table(seed,policy,reward,M.generatedPackets,M.receivedPackets,M.lostPackets, ...
            M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss, ...
            M.meanConsecutiveLoss,handovers,M.phyLossPackets,M.handoverLossPackets, ...
            M.outageLossPackets,causes,'VariableNames',{'packetSeed','policy','reward', ...
            'generated','received','lost','loss_pct','onTime_pct','maxConsecutiveLoss', ...
            'meanConsecutiveLoss','handovers','phyLoss','handoverLoss','outageLoss','verifiedLoss_pct'});
        comparison=[comparison;row];
        % Keep full packet evidence for the first held-out seed.
        if seedIndex==1
            writetable(P,fullfile(O.outputDir,char(policy+"_packets.csv")));
            writetable(M.lossRuns,fullfile(O.outputDir,char(policy+"_loss_runs.csv")));
        end
        writetable(comparison,fullfile(O.outputDir,'evaluation_summary.csv'));
        fprintf('Evaluation seed %d | %s | loss %.3f%% | on time %.3f%% | max run %d\n', ...
            seed,policy,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss);
    end
end
disp(comparison);
end
