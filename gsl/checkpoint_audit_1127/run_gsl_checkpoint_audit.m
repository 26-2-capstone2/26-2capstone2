function runs=run_gsl_checkpoint_audit()
gsl=setupGSLCheckpointAudit();here=fileparts(mfilename('fullpath'));out=fullfile(here,'results');if ~isfolder(out),mkdir(out);end
source=fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356');D=load(fullfile(source,'study.mat'),'R');R=D.R;
C=configGSLToolboxPHY(R.config);D=load(fullfile(source,'geometry.mat'),'geometry');G=D.geometry;
seeds=20279301:20279310;episodes=100:100:1000;assert(isempty(intersect(seeds,R.options.trainingSeeds)));
assert(C.numPlanes==6&&C.satsPerPlane==11&&C.duration_s==600);
referenceStates=cell(10,600);referencePER=cell(10,600);referenceOld=zeros(10,600);referenceChosen=zeros(10,600);
referenceDraws=cell(10,1);referenceSNR=cell(10,1);floorMax=zeros(10,1);referencePackets=cell(10,1);
runs=table();fixedScores=table();
geometry=G;save(fullfile(out,'geometry.mat'),'geometry','-v7');
training=R.training;writetable(training,fullfile(out,'original_training.csv'));
for episode=episodes
    D=load(fullfile(source,sprintf('agent_episode_%04d.mat',episode)),'checkpoint');checkpoint=D.checkpoint;O=checkpoint.options;
    assert(O.discountFactor==.95&&O.qHysteresis==.02&&numel(O.featureNames)==11);
    assert(O.rewardWeights.onTime==1&&O.rewardWeights.burst==.3&&O.rewardWeights.handover==.1);
    agent=GSLTrendDoubleDQN(O);agent.restore(checkpoint);before=agent.updateCount;
    for repeat=1:10
        seed=seeds(repeat);env=GSLTrendEpisode(C,G,O,seed);trace=zeros(600,12);fixed=zeros(600,13);
        for t=1:600
            S=env.observe();q=agent.values(S);[id,ix,blocked]=choose(S,q,O.qHysteresis);oldID=env.servingID;
            chosenPER=1;bestPER=1;qChosen=NaN;qMax=NaN;expected=60;
            if ix>0
                per=env.per(t,S.ids);chosenPER=per(ix);bestPER=min(per);qChosen=q(ix);qMax=max(q);
                ho=oldID>0&&oldID~=id;expected=6*ho+(60-6*ho)*chosenPER;
            end
            trace(t,:)=[t-1 oldID id qChosen qMax blocked chosenPER bestPER expected env.streak 0 0];
            if episode==100
                referenceStates{repeat,t}=S;referencePER{repeat,t}=env.per(t,S.ids);referenceOld(repeat,t)=oldID;referenceChosen(repeat,t)=id;
                Sq=S;qr=q;
            else
                Sq=referenceStates{repeat,t};qr=agent.values(Sq);
            end
            [fixedID,jx,fixedBlocked]=choose(Sq,qr,O.qHysteresis);
            baseID=referenceChosen(repeat,t);baseIx=find(Sq.ids==baseID,1);fp=1;bp=1;fb=1;qe=NaN;qb=NaN;ex=60;eb=60;
            if jx>0
                pp=referencePER{repeat,t};fp=pp(jx);bp=min(pp);fb=pp(baseIx);qe=qr(jx);qb=qr(baseIx);
                old=referenceOld(repeat,t);h=old>0&&old~=fixedID;hb=old>0&&old~=baseID;
                ex=6*h+(60-6*h)*fp;eb=6*hb+(60-6*hb)*fb;
            end
            fixed(t,:)=[episode repeat seed t-1 baseID fixedID qe qb fp fb bp ex-eb fixedBlocked];
            [~,reward,~]=env.step(id);trace(t,11)=reward;
        end
        [P,M,L]=env.results();assert(M.pendingPackets==0&&M.latePackets==0);
        if episode==100
            referenceDraws{repeat}=env.draws;referenceSNR{repeat}=env.snr;referencePackets{repeat}=P;
            minPER=ones(600,1);for t=1:600,v=G.isVisible(t,:);if any(v),minPER(t)=min(env.per(t,v));end;end
            oracle=env.draws<repelem(minPER,60);floorMax(repeat)=maxRun(oracle);assert(all(~oracle|env.loss));
            p=fullfile(gsl,'nstep_1127/results_n1');rpath=fullfile(p,strtrim(fileread(fullfile(p,'latest_result.txt'))));
            D=load(fullfile(rpath,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');
            assert(isequal(P.lost,D.preview.P.lost)&&isequal(L.servingSatID,D.preview.L.servingSatID),'CHECKPOINT:Original100Mismatch');
        else
            assert(isequal(env.draws,referenceDraws{repeat})&&isequal(env.snr,referenceSNR{repeat}));
        end
        sampled=0;for t=600:-1:1,sampled=env.rewardHistory(t)+O.discountFactor*sampled;trace(t,12)=sampled;end
        traceTable=array2table(trace,'VariableNames',{'time_s','previousSatID','chosenSatID','predictedQ','maxQ','blockedByQMargin','chosenPER','bestPER','expectedFirstSecondLoss','incomingStreak','reward','sampledFrozenPolicyReturn'});
        traceTable.QminusSampledPolicyReturn=traceTable.predictedQ-traceTable.sampledFrozenPolicyReturn;
        fixedTable=array2table(fixed,'VariableNames',{'episode','repeat','seed','time_s','reference100SatID','currentModelSatID','QcurrentChoice','QreferenceChoice','PERcurrentChoice','PERreferenceChoice','bestPER','expectedLossDifference','blockedByQMargin'});
        fixedScores=[fixedScores;fixedTable]; %#ok<AGROW>
        [~,j]=max(M.lossRuns.length_packets);burst=M.lossRuns(j,:);
        folder=fullfile(out,sprintf('episode_%04d_repeat_%02d',episode,repeat));mkdir(folder);
        writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));writetable(L,fullfile(folder,'decisions.csv'));writetable(traceTable,fullfile(folder,'decision_quality.csv'));
        preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',sprintf('DDQN_episode_%d',episode),'seed',seed);save(fullfile(folder,'preview.mat'),'preview','-v7.3');
        switches=sum(fixedTable.currentModelSatID~=fixedTable.reference100SatID);
        row=table(episode,repeat,seed,M.generatedPackets,M.receivedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss, ...
            sum(env.handovers),M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets, ...
            sum(env.rewardHistory),trace(1,12),floorMax(repeat),M.maxConsecutiveLoss-floorMax(repeat),switches, ...
            burst.firstGeneration_s,burst.lastGeneration_s, ...
            'VariableNames',{'episode','repeat','seed','generated','received','lost','loss_pct','onTime_pct','maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','late','pending', ...
            'undiscountedReward','discountedStartReturn','optimisticMax','excessMaxAboveFloor','differentChoicesOnReferenceStates','maxBurstStart_s','maxBurstEnd_s'});
        runs=[runs;row];writetable(runs,fullfile(out,'runs.csv')); %#ok<AGROW>
        fprintf('CHECKPOINT %04d %02d/10 | loss %.4f%% | max %d | floor %d | HO %d | fixed-state changes %d/600\n', ...
            episode,repeat,M.packetLossRatio,M.maxConsecutiveLoss,floorMax(repeat),sum(env.handovers),switches);
    end
    assert(agent.updateCount==before);writetable(fixedScores,fullfile(out,'reference_state_scores.csv'));
end
save(fullfile(out,'study.mat'),'runs','C','seeds','episodes','source','-v7.3');
save(fullfile(out,'reference_states.mat'),'referenceStates','referencePER','referenceOld','referenceChosen','floorMax','-v7.3');
fprintf('CHECKPOINT AUDIT COMPLETE: 10 saved models x 10 paired seeds, epsilon=0, no learning.\n');
end
function [id,ix,blocked]=choose(S,q,margin)
id=0;ix=0;blocked=false;if isempty(S.ids),return;end
[~,ix]=max(q);old=find(S.features(4,:)>0,1);
if ~isempty(old)&&q(ix)<q(old)+margin,blocked=ix~=old;ix=old;end
id=S.ids(ix);
end
function m=maxRun(lost)
e=diff([false;logical(lost(:));false]);v=find(e==-1)-find(e==1);m=0;if ~isempty(v),m=max(v);end
end
