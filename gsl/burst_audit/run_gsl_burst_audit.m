function R=run_gsl_burst_audit(ddqnRoot,maxsnrRoot)
% Frozen policy replay, decision evidence, and a no-retraining Q-gate ablation.
if nargin<1
    parent=fileparts(fileparts(mfilename('fullpath')));
    root=fullfile(parent,'ddqn_6x11','results_ddqn_6x11');ddqnRoot=fullfile(root,strtrim(fileread(fullfile(root,'latest_result.txt'))));
    root=fullfile(parent,'maxsnr_comparison','results_maxsnr');maxsnrRoot=fullfile(root,strtrim(fileread(fullfile(root,'latest_result.txt'))));
end
S=load(fullfile(ddqnRoot,'study.mat'),'R');study=S.R;O=study.options;C=configGSLToolboxPHY(study.config);
S=load(fullfile(ddqnRoot,'geometry.mat'),'geometry');G=S.geometry;
S=load(fullfile(ddqnRoot,'agent.mat'),'checkpoint');agent=GSLTrendDoubleDQN(O);agent.restore(S.checkpoint);before=agent.updateCount;
root=fullfile(fileparts(mfilename('fullpath')),'results_burst_audit');if ~isfolder(root),mkdir(root);end
out=fullfile(root,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
allDecisions=table();allBursts=table();ablation=table();
for repeat=1:10
    S=load(fullfile(ddqnRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');D=S.preview;
    S=load(fullfile(maxsnrRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');X=S.preview;
    env=GSLTrendEpisode(C,G,O,D.seed);env0=GSLTrendEpisode(C,G,O,D.seed);
    assert(isequal(env.snr,D.snr) && isequal(env.draws,D.P.phyRandomDraw));
    log=table();candidateLog=table();localAlternative=false(36000,1);
    for t=0:599
        obs=env.observe();q=double(agent.values(obs));[qBest,jBest]=max(q);
        [~,jSNR]=max(obs.snr);old=find(obs.ids==env.servingID,1);qOld=NaN;gap=NaN;gated=false;
        if ~isempty(old),qOld=q(old);gap=qBest-qOld;end
        ix=jBest;
        if ~isempty(old) && gap<O.qHysteresis
            ix=old;gated=jBest~=old;
        end
        assert(ix==agent.select(obs,0,O.qHysteresis),'GSL:PolicyReplayMismatch');
        id=obs.ids(ix);same=id==env.servingID;reason="switch_or_acquire";
        if same && gated,reason="retain_Q_margin";elseif same,reason="retain_Q_argmax";end
        assert(id==D.L.servingSatID(t+1),'GSL:SavedChoiceMismatch');
        rows=t*60+(1:60).';u=(0:59).'/60;
        alternativeHO=env.servingID>0 && obs.ids(jSNR)~=env.servingID;
        localAlternative(rows)=(alternativeHO & u<C.handoverInterruption_s-16*eps(max(1,t+1))) ...
            | env.draws(rows)<env.per(t+1,obs.ids(jSNR));
        p=env.per(t+1,id);pBest=env.per(t+1,obs.ids(jSNR));
        row=table(repeat,t,env.servingID,id,obs.ids(jSNR),obs.ids(jBest), ...
            obs.snr(ix),obs.snr(jSNR),p,pBest,q(ix),qBest,qOld,gap,gated,same,reason, ...
            env.streak,obs.delta(ix),obs.trend5_dB_per_s(ix), ...
            sum(D.P.lost(rows)),sum(localAlternative(rows)), ...
            'VariableNames',{'repeat','time_s','previousID','chosenID','maxSNR_ID','maxQ_ID', ...
            'chosenSNR_dB','bestSNR_dB','chosenPER','bestPER','chosenQ','bestQ','previousQ','Qgap', ...
            'marginBlockedSwitch','retained','reason','priorStreak','delta1_dB','trend5_dB_per_s', ...
            'actualLossCount','oneStepMaxSNRLossCount'});
        log=[log;row]; %#ok<AGROW>
        n=numel(obs.ids);candidateLog=[candidateLog;table(repmat(t,n,1),obs.ids,obs.snr, ...
            obs.elevation,obs.delta,obs.trend5_dB_per_s,env.per(t+1,obs.ids).',q.', ...
            obs.ids==env.servingID,obs.ids==id, ...
            'VariableNames',{'time_s','satelliteID','snr_dB','elevation_deg','delta1_dB','trend5_dB_per_s', ...
            'PER','Q','wasServing','chosen'})]; %#ok<AGROW>
        env.step(id);
        obs0=env0.observe();ix0=agent.select(obs0,0,0);env0.step(obs0.ids(ix0));
    end
    assert(isequal(env.loss,logical(D.P.lost)) && isequal(env.received,logical(D.P.received)));
    folder=fullfile(out,sprintf('repeat_%02d',repeat));mkdir(folder);
    writetable(log,fullfile(folder,'decisions_with_Q.csv'));writetable(candidateLog,fullfile(folder,'candidate_Q.csv'));
    [P0,M0,L0]=env0.results();
    writetable(P0,fullfile(folder,'no_margin_packets.csv'));writetable(L0,fullfile(folder,'no_margin_decisions.csv'));
    writetable(M0.lossRuns,fullfile(folder,'no_margin_loss_runs.csv'));
    A=table(repeat,D.seed,D.M.packetLossRatio,M0.packetLossRatio,D.M.maxConsecutiveLoss,M0.maxConsecutiveLoss, ...
        sum(D.L.handoverEvent),sum(L0.handoverEvent),sum(log.marginBlockedSwitch), ...
        'VariableNames',{'repeat','seed','originalLoss_pct','noMarginLoss_pct','originalMaxRun','noMarginMaxRun', ...
        'originalHandovers','noMarginHandovers','blockedDecisions'});
    ablation=[ablation;A]; %#ok<AGROW>
    B=D.M.lossRuns;[~,longest]=max(B.length_packets);
    keep=find(B.length_packets>=30);keep=unique([keep;longest]);
    for k=keep.'
        a=B.firstPacketID(k);b=B.lastPacketID(k);times=unique(floor(D.P.time_s(a:b)));
        L=log(times+1,:);rows=(a:b).';
        indices=ismember(candidateLog.time_s,max(0,times(1)-2):min(599,times(end)+2));
        writetable(candidateLog(indices,:),fullfile(folder,sprintf('burst_%d_%d_candidates.csv',a,b)));
        J=L.retained & L.bestPER<L.chosenPER;
        row=table(repeat,a,b,B.length_packets(k),D.P.time_s(a),D.P.time_s(b), ...
            k==longest,sum(D.P.phy_loss(rows)),sum(D.P.handover_loss(rows)), ...
            sum(L.retained),sum(L.marginBlockedSwitch),sum(J),sum(L.marginBlockedSwitch & J), ...
            min(L.chosenSNR_dB),min(L.bestSNR_dB),max(L.chosenPER),max(L.bestPER), ...
            sum(X.P.lost(rows)),sum(localAlternative(rows)),sum(P0.lost(rows)), ...
            'VariableNames',{'repeat','firstPacketID','lastPacketID','length','start_s','end_s','isLongest', ...
            'phyLoss','handoverLoss','retainedDecisions','marginBlocks','retainsWithBetterPHYAlternative', ...
            'marginBlocksWithBetterAlternative','minChosenSNR','minBestSNR','maxChosenPER','maxBestPER', ...
            'maxSNRLossesAtSameIDs','oneStepAlternativeLosses','noMarginLossesAtSameIDs'});
        allBursts=[allBursts;row]; %#ok<AGROW>
    end
    allDecisions=[allDecisions;log]; %#ok<AGROW>
    writetable(allBursts,fullfile(out,'burst_evidence.csv'));writetable(ablation,fullfile(out,'no_margin_ablation.csv'));
    fprintf('AUDIT %02d/10 | exact replay PASS | Q margin blocks %d | max run %d -> no-margin %d\n', ...
        repeat,sum(log.marginBlockedSwitch),D.M.maxConsecutiveLoss,M0.maxConsecutiveLoss);
end
assert(agent.updateCount==before);
writetable(allDecisions,fullfile(out,'all_decisions_with_Q.csv'));
R=struct('outputDir',out,'ddqnRoot',ddqnRoot,'maxsnrRoot',maxsnrRoot,'bursts',allBursts, ...
    'decisions',allDecisions,'ablation',ablation,'frozenNetworkVerified',true,'exactReplayVerified',true);
save(fullfile(out,'audit.mat'),'R','-v7.3');
[~,name]=fileparts(out);fid=fopen(fullfile(root,'latest_result.txt'),'w');fprintf(fid,'%s',name);fclose(fid);
disp(allBursts(allBursts.isLongest,:));disp(ablation);
fprintf('BURST AUDIT COMPLETE: %s\n',out);
end
