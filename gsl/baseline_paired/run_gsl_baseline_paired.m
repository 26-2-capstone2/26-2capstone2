function R=run_gsl_baseline_paired(ddqnRoot)
% Evaluate original elevation + 4 deg policy; no learning or network changes.
if nargin<1
    parent=fileparts(fileparts(mfilename('fullpath')));
    resultRoot=fullfile(parent,'ddqn_6x11','results_ddqn_6x11');
    folder=strtrim(fileread(fullfile(resultRoot,'latest_result.txt')));ddqnRoot=fullfile(resultRoot,folder);
end
S=load(fullfile(ddqnRoot,'study.mat'),'R');source=S.R;
O=source.options;C=configGSLToolboxPHY(source.config);
S=load(fullfile(ddqnRoot,'geometry.mat'),'geometry');G=S.geometry;
assert(C.numPlanes==6 && C.satsPerPlane==11 && O.environmentLoss_dB==6);
assert(C.handoverMargin_deg==4 && height(source.runs)==10);
outRoot=fullfile(fileparts(mfilename('fullpath')),'results_baseline_paired');
if ~isfolder(outRoot),mkdir(outRoot);end
out=fullfile(outRoot,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
geometry=G;save(fullfile(out,'geometry.mat'),'geometry','-v7');
[ids,handovers,selection]=selectServingSatellite(G.elevation_deg,G.isVisible,C.handoverMargin_deg);
writetable(selection,fullfile(out,'selection_policy.csv'));
runs=table();pairing=table();
for repeat=1:height(source.runs)
    seed=source.runs.seed(repeat);
    assert(seed==O.evaluationSeeds(repeat));
    S=load(fullfile(ddqnRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');D=S.preview;
    env=GSLSelectionEpisode(C,G,O,seed);
    assert(isequal(env.snr,D.snr),'GSL:UnpairedChannel');
    assert(isequal(env.draws,D.P.phyRandomDraw),'GSL:UnpairedPacketDraws');
    rows=find(D.P.attempted);ix=sub2ind(size(env.per),floor(D.P.time_s(rows))+1,D.P.servingSatID(rows));
    assert(max(abs(env.per(ix)-D.P.phyPER(rows)))<1e-12,'GSL:PHYTableChanged');
    for t=1:C.duration_s,env.step(ids(t));end
    [P,M,L]=env.results();
    assert(isequal(L.servingSatID(1:600),ids(1:600)));
    assert(isequal(L.handoverEvent(1:600),handovers(1:600)));
    assert(isequal(P.phyRandomDraw,D.P.phyRandomDraw));
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
    preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',"Elevation_4deg",'seed',seed); %#ok<NASGU>
    save(fullfile(folder,'preview.mat'),'preview','-v7.3');
    pairing=[pairing;table(repeat,seed,true,true,true,true, ...
        'VariableNames',{'repeat','seed','sameGeometry','sameAllSatelliteSNR','samePacketDraws','samePERModel'})]; %#ok<AGROW>
    writetable(runs,fullfile(out,'baseline_runs.csv'));writetable(pairing,fullfile(out,'pairing_checks.csv'));
    fprintf('BASELINE %02d/10 | loss %.4f%% | on-time %.4f%% | max run %d | HO %d | paired inputs PASS\n', ...
        repeat,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(L.handoverEvent));
end
assert(all(runs.pending==0) && all(abs(runs.loss_pct-runs.verifiedLoss_pct)<1e-10));
comparison=table();paired=table();combined=table();
for metric=["loss_pct","onTime_pct","maxLossRun","handovers"]
    a=runs.(metric);b=source.runs.(metric);delta=b-a;half=2.26215716274099*std(delta)/sqrt(10);
    relative=100*(mean(b)-mean(a))/mean(a);
    comparison=[comparison;table(metric,mean(a),std(a),mean(b),std(b),mean(delta),relative, ...
        mean(delta)-half,mean(delta)+half, ...
        'VariableNames',{'metric','baseline_mean','baseline_std','ddqn_mean','ddqn_std','ddqnMinusBaseline', ...
        'relativeChange_pct','pairedDelta_lower95','pairedDelta_upper95'})]; %#ok<AGROW>
    paired=[paired;table(runs.repeat,runs.seed,repmat(metric,10,1),a,b,delta, ...
        'VariableNames',{'repeat','seed','metric','baseline','ddqn','ddqnMinusBaseline'})]; %#ok<AGROW>
end
for policy=["Elevation_4deg","DDQN_5s_trend"]
    T=runs;if policy=="DDQN_5s_trend",T=source.runs;end
    T.policy=repmat(policy,height(T),1);combined=[combined;T]; %#ok<AGROW>
end
writetable(comparison,fullfile(out,'comparison_summary.csv'));
writetable(paired,fullfile(out,'paired_differences.csv'));writetable(combined,fullfile(out,'all_runs.csv'));
writetable(source.runs,fullfile(out,'ddqn_runs.csv'));
R=struct('outputDir',out,'ddqnRoot',ddqnRoot,'config',C,'baseline',runs,'ddqn',source.runs, ...
    'comparison',comparison,'paired',paired,'pairingChecks',pairing,'baselineTrainingEpisodes',0);
save(fullfile(out,'comparison.mat'),'R','-v7.3');
[~,name]=fileparts(out);fid=fopen(fullfile(outRoot,'latest_result.txt'),'w');fprintf(fid,'%s',name);fclose(fid);
plotGSLPairedComparison(R,false);disp(comparison);
fprintf('PAIRED BASELINE COMPLETE | no training | existing frozen DDQN results reused\n%s\n',out);
end
