function cases=audit_gsl_burst_counterfactual()
source=setupGSLBurstAudit();here=fileparts(mfilename('fullpath'));out=fullfile(here,'results');mkdir(out);
cases=table();branches=table();probes=table();
for n=[1 3 5]
    base=fullfile(source,sprintf('results_n%d',n));folder=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
    D=load(fullfile(folder,'study.mat'),'R');R=D.R;O=R.options;C=configGSLToolboxPHY(R.config);
    D=load(fullfile(folder,'geometry.mat'),'geometry');G=D.geometry;
    D=load(fullfile(folder,'agent.mat'),'checkpoint');agent=GSLNStepDoubleDQN(O);agent.restore(D.checkpoint);updates=agent.updateCount;
    for repeat=1:10
        seed=R.runs.seed(repeat);D=load(fullfile(folder,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');saved=D.preview;
        P=saved.P;lossRuns=saved.M.lossRuns;[originalMax,j]=max(lossRuns.length_packets);target=lossRuns(j,:);
        first=target.firstPacketID;last=target.lastPacketID;t0=floor(P.generationTime_s(first));tEnd=floor(P.generationTime_s(last));
        start=max(0,t0-3);stop=min(C.duration_s,tEnd+3);rows=(start*60+1:stop*60).';
        env=GSLTrendAuditEpisode(C,G,O,seed);snapshots=cell(stop-start,1);
        assert(isequal(env.snr,saved.snr)&&isequal(env.draws,P.phyRandomDraw));
        for t=0:C.duration_s-1
            if t>=start&&t<stop,snapshots{t-start+1}=copy(env);end
            S=env.observe();id=choose(agent,S,O.qHysteresis);env.step(id);
        end
        assert(isequal(env.loss,logical(P.lost))&&isequal(env.selected,saved.L.servingSatID(1:600)));
        baselineLoss=env.loss;baselineWindowMax=maxRun(baselineLoss(rows));baselineWindowLost=sum(baselineLoss(rows));
        minPER=ones(600,1);
        for t=1:600,v=G.isVisible(t,:);if any(v),minPER(t)=min(env.per(t,v));end;end
        packetMinPER=repelem(minPER,60);oracleLoss=env.draws<packetMinPER;
        assert(all(~oracleLoss|baselineLoss),'AUDIT:NotALowerBound');
        oracleGlobalMax=maxRun(oracleLoss);oracleBurstMax=maxRun(oracleLoss(first:last));
        bestScore=[baselineWindowMax baselineWindowLost sum(env.handovers(start+1:stop))];best=[];bestTime=NaN;bestID=NaN;
        for k=1:numel(snapshots)
            before=snapshots{k};S=before.observe();q=agent.values(S);actual=env.selected(before.time+1);
            actualIndex=find(S.ids==actual,1);old=find(S.ids==before.servingID,1);[~,rawBest]=max(q);
            blocked=~isempty(old)&&rawBest~=old&&actual==before.servingID&&q(rawBest)>q(old)&&q(rawBest)<q(old)+O.qHysteresis;
            oldQ=NaN;if ~isempty(old),oldQ=q(old);end
            probe=table(n,repeat,seed,before.time,before.servingID,actual,S.ids(rawBest),q(rawBest)-oldQ,blocked, ...
                before.per(before.time+1,actual),min(before.per(before.time+1,S.ids)),before.streak, ...
                'VariableNames',{'nStep','repeat','seed','time_s','previousSatID','chosenSatID','rawBestQSatID','bestQMinusServingQ','blockedByQMargin','chosenPER','bestPER','incomingStreak'});
            probes=[probes;probe]; %#ok<AGROW>
            for a=1:numel(S.ids)
                id=S.ids(a);fork=copy(before);[~,firstReward]=fork.step(id);
                while fork.time<stop,F=fork.observe();fork.step(choose(agent,F,O.qHysteresis));end
                assert(before.time==start+k-1&&isequal(before.loss(1:before.time*60),baselineLoss(1:before.time*60)));
                if id==actual,assert(isequal(fork.loss(rows),baselineLoss(rows)),'AUDIT:ForkReferenceMismatch');end
                windowMax=maxRun(fork.loss(rows));windowLost=sum(fork.loss(rows));windowHO=sum(fork.handovers(start+1:stop));
                per=before.per(before.time+1,id);isHO=before.servingID>0&&before.servingID~=id;
                expectedLost=6*isHO+(60-6*isHO)*per;
                row=table(n,repeat,seed,before.time,id,id==actual,id==before.servingID,per,q(a),q(a)-q(actualIndex), ...
                    isHO,expectedLost,firstReward,windowMax,windowLost,windowHO, ...
                    'VariableNames',{'nStep','repeat','seed','probeTime_s','forcedSatID','isOriginalChoice','isStay','PER','Q','QminusOriginalChoice','handoverAtIntervention','expectedFirstSecondLoss','firstReward','windowMaxRun','windowLost','windowHandovers'});
                branches=[branches;row]; %#ok<AGROW>
                score=[windowMax windowLost windowHO];different=find(score~=bestScore,1);
                if ~isempty(different)&&score(different)<bestScore(different)
                    bestScore=score;best=copy(fork);bestTime=before.time;bestID=id;
                end
            end
        end
        if isempty(best),best=copy(env);end
        while best.time<600,S=best.observe();best.step(choose(agent,S,O.qHysteresis));end
        fullMax=maxRun(best.loss);fullLost=sum(best.loss);
        assert(all(~oracleLoss|best.loss)&&fullMax>=oracleGlobalMax);
        full=table((1:36000).',P.generationTime_s,baselineLoss,best.loss,oracleLoss,packetMinPER, ...
            'VariableNames',{'packetID','generationTime_s','originalLost','counterfactualLost','optimisticAllCandidatesFail','bestCandidatePER'});
        writetable(full,fullfile(out,sprintf('n%d_repeat_%02d_packet_comparison.csv',n,repeat)));
        row=table(n,repeat,seed,first,last,originalMax,t0,tEnd,sum(P.phy_loss(first:last)),sum(P.handover_loss(first:last)), ...
            sum(oracleLoss(first:last)),sum(packetMinPER(first:last)==1),oracleBurstMax,oracleGlobalMax, ...
            start,stop,baselineWindowMax,bestScore(1),bestTime,bestID,sum(baselineLoss),fullLost,fullMax,sum(env.handovers),sum(best.handovers), ...
            'VariableNames',{'nStep','repeat','seed','firstPacketID','lastPacketID','originalMaxRun','burstStartSecond','burstEndSecond','burstPHYLoss','burstHOLoss', ...
            'allCandidatesFailPacketsInBurst','allCandidatesPER1PacketsInBurst','optimisticMaxWithinBurst','optimisticGlobalMax', ...
            'windowStart_s','windowStop_s','originalWindowMax','bestWindowMax','bestProbeTime_s','bestForcedSatID','originalFullLost','counterfactualFullLost','counterfactualGlobalMax','originalHandovers','counterfactualHandovers'});
        cases=[cases;row]; %#ok<AGROW>
        writetable(cases,fullfile(out,'cases.csv'));writetable(branches,fullfile(out,'all_branches.csv'));writetable(probes,fullfile(out,'probe_states.csv'));
        fprintf('AUDIT n%d %02d/10 | max %d | optimistic lower bound %d | best local %d | full counterfactual max %d | forced t %.0f ID %.0f\n', ...
            n,repeat,originalMax,oracleGlobalMax,bestScore(1),fullMax,bestTime,bestID);
        assert(agent.updateCount==updates);
    end
end
save(fullfile(out,'audit.mat'),'cases','branches','probes','-v7.3');
fprintf('AUDIT COMPLETE: 30 original rollouts verified, exact independent forks, no training, frozen weights.\n');
end
function id=choose(agent,S,margin)
id=0;if isempty(S.ids),return;end
q=agent.values(S);[~,ix]=max(q);old=find(S.features(4,:)>0,1);
if ~isempty(old)&&q(ix)<q(old)+margin,ix=old;end
id=S.ids(ix);
end
function m=maxRun(lost)
e=diff([false;logical(lost(:));false]);v=find(e==-1)-find(e==1);m=0;if ~isempty(v),m=max(v);end
end
