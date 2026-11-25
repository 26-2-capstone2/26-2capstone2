function R=run_gsl_maxsnr_comparison(ddqnRoot,baselineRoot)
% Pure greedy SNR: no learning, no hysteresis, decision interval one second.
parent=fileparts(fileparts(mfilename('fullpath')));
if nargin<1
    root=fullfile(parent,'ddqn_6x11','results_ddqn_6x11');
    ddqnRoot=fullfile(root,strtrim(fileread(fullfile(root,'latest_result.txt'))));
end
if nargin<2
    root=fullfile(parent,'baseline_paired','results_baseline_paired');
    baselineRoot=fullfile(root,strtrim(fileread(fullfile(root,'latest_result.txt'))));
end
S=load(fullfile(ddqnRoot,'study.mat'),'R');D=S.R;
S=load(fullfile(baselineRoot,'comparison.mat'),'R');B=S.R;
assert(isequaln(D.runs,B.ddqn),'GSL:DifferentDDQNReference');
O=D.options;C=configGSLToolboxPHY(D.config);
assert(C.numPlanes==6 && C.satsPerPlane==11 && O.environmentLoss_dB==6);
S=load(fullfile(ddqnRoot,'geometry.mat'),'geometry');G=S.geometry;
root=fullfile(fileparts(mfilename('fullpath')),'results_maxsnr');
if ~isfolder(root),mkdir(root);end
out=fullfile(root,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
geometry=G;save(fullfile(out,'geometry.mat'),'geometry','-v7');
runs=table();pairing=table();
for repeat=1:height(D.runs)
    seed=D.runs.seed(repeat);assert(seed==O.evaluationSeeds(repeat));
    S=load(fullfile(ddqnRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');Pddqn=S.preview;
    env=GSLSelectionEpisode(C,G,O,seed);
    assert(isequal(env.snr,Pddqn.snr) && isequal(env.draws,Pddqn.P.phyRandomDraw));
    attempted=find(Pddqn.P.attempted);
    index=sub2ind(size(env.per),floor(Pddqn.P.time_s(attempted))+1,Pddqn.P.servingSatID(attempted));
    assert(max(abs(env.per(index)-Pddqn.P.phyPER(attempted)))<1e-12,'GSL:PHYChanged');
    for t=1:C.duration_s
        obs=env.observe();ix=selectGSLThreeAction(obs,"MaxSNR",O,[]);id=0;
        if ix>0
            id=obs.ids(ix);
            bestSNR=max(env.snr(t,G.isVisible(t,:)));
            assert(abs(obs.snr(ix)-bestSNR)<1e-12,'GSL:NotMaxSNR');
        end
        env.step(id);
    end
    [P,M,L]=env.results();
    row=table(repeat,seed,M.generatedPackets,M.receivedPackets,M.lostPackets, ...
        M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(L.handoverEvent), ...
        M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets, ...
        100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets, ...
        'VariableNames',{'repeat','seed','generated','received','lost','loss_pct','onTime_pct','maxLossRun', ...
        'handovers','phyLoss','handoverLoss','outageLoss','late','pending','verifiedLoss_pct'});
    runs=[runs;row]; %#ok<AGROW>
    folder=fullfile(out,sprintf('repeat_%02d',repeat));mkdir(folder);
    writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));
    writetable(L,fullfile(folder,'decisions.csv'));
    preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',"MaxSNR_no_hysteresis",'seed',seed); %#ok<NASGU>
    save(fullfile(folder,'preview.mat'),'preview','-v7.3');
    pairing=[pairing;table(repeat,seed,true,true,true,true, ...
        'VariableNames',{'repeat','seed','sameGeometry','sameAllSatelliteSNR','samePacketDraws','samePERModel'})]; %#ok<AGROW>
    writetable(runs,fullfile(out,'maxsnr_runs.csv'));writetable(pairing,fullfile(out,'pairing_checks.csv'));
    fprintf('MAX-SNR %02d/10 | loss %.4f%% | on-time %.4f%% | max run %d | HO %d | greedy and paired inputs PASS\n', ...
        repeat,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(L.handoverEvent));
end
assert(height(runs)==10 && all(runs.pending==0) && all(abs(runs.loss_pct-runs.verifiedLoss_pct)<1e-10));
summary=table();paired=table();allRuns=table();names=["Elevation_4deg","MaxSNR_no_hysteresis","DDQN_5s_trend"];
tables={B.baseline,runs,D.runs};metrics=["loss_pct","onTime_pct","maxLossRun","handovers"];
for k=1:3
    T=tables{k};assert(isequal(T.seed,D.runs.seed));
    T.policy=repmat(names(k),height(T),1);allRuns=[allRuns;T]; %#ok<AGROW>
    for metric=metrics
        values=T.(metric);
        summary=[summary;table(names(k),metric,mean(values),std(values),min(values),max(values), ...
            'VariableNames',{'policy','metric','mean','std','min','max'})]; %#ok<AGROW>
    end
end
for metric=metrics
    delta=D.runs.(metric)-runs.(metric);half=2.26215716274099*std(delta)/sqrt(10);
    paired=[paired;table(metric,mean(runs.(metric)),mean(D.runs.(metric)),mean(delta), ...
        100*mean(delta)/mean(runs.(metric)),mean(delta)-half,mean(delta)+half, ...
        'VariableNames',{'metric','maxsnr_mean','ddqn_mean','ddqnMinusMaxSNR','relativeChange_pct', ...
        'pairedDelta_lower95','pairedDelta_upper95'})]; %#ok<AGROW>
end
writetable(summary,fullfile(out,'three_policy_summary.csv'));writetable(allRuns,fullfile(out,'all_runs.csv'));
writetable(paired,fullfile(out,'ddqn_vs_maxsnr.csv'));
writetable(B.baseline,fullfile(out,'baseline_runs.csv'));writetable(D.runs,fullfile(out,'ddqn_runs.csv'));
R=struct('outputDir',out,'ddqnRoot',ddqnRoot,'baselineRoot',baselineRoot,'config',C, ...
    'baseline',B.baseline,'maxsnr',runs,'ddqn',D.runs,'summary',summary,'paired',paired,'pairingChecks',pairing);
save(fullfile(out,'comparison.mat'),'R','-v7.3');
[~,folder]=fileparts(out);fid=fopen(fullfile(root,'latest_result.txt'),'w');fprintf(fid,'%s',folder);fclose(fid);
plotGSLMaxSNRComparison(R,false);disp(paired);
fprintf('MAX-SNR COMPARISON COMPLETE | no new learning | 10 paired evaluations\n%s\n',out);
end
