function R=run_gsl_hysteresis_comparison(modelPath,CFG,seeds)
% Frozen DDQN, four evaluation gates, ten paired 600-second episodes by default.
root=fileparts(mfilename('fullpath'));
if nargin<1 || isempty(modelPath)
    modelPath=fullfile(root,'results_ddqn','20261112_163509_823','agent.mat');
end
if nargin<2 || isempty(CFG), CFG=configGSL(); end
if nargin<3 || isempty(seeds), seeds=20265001:20265010; end
validateattributes(seeds,{'numeric'},{'vector','integer','nonnegative','finite'});
assert(numel(unique(seeds))==numel(seeds),'GSL:DuplicateSeeds');
assert(isfile(modelPath),'GSL:MissingModel','Saved agent not found: %s',modelPath);
S=load(modelPath,'agent'); agent=S.agent;
CFG.makePlots=false; CFG.openPacketViewer=false; CFG.exportResults=false;
outDir=fullfile(root,'results_hysteresis',char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));
mkdir(outDir);
env=GSLRLEnvironment([],CFG);
state=env.observe();
assert(agent.onlineNetwork.Layers(1).InputSize==numel(state.vector) && ...
    agent.onlineNetwork.Layers(end).OutputSize==env.maxCandidateCount,'GSL:ModelCapacity');
margins=[0 .1 .3 .5]; raw=table();
fprintf('Frozen DDQN model: %s\n0 dB = gate OFF; positive margins = proposed SNR >= serving SNR + margin.\n',modelPath);
for repeat=1:numel(seeds)
    packetSeed=seeds(repeat); snrSeed=mod(double(CFG.snrRandomSeed)+double(packetSeed),2^32);
    for margin=margins
        env.reset(packetSeed,snrSeed); done=false; handovers=0; blockedCount=0;
        logs=zeros(CFG.duration_s,9); k=0;
        while ~done
            state=env.observe(); T=env.allCandidates();
            proposed=selectGSLDDQNSatelliteID(agent,state);
            [selected,blocked]=applyGSLHysteresis(proposed,T,margin);
            old=find(T.isServing,1); oldSNR=NaN; if ~isempty(old), oldSNR=T.snr_dB(old); end
            proposedSNR=NaN; if proposed>0, proposedSNR=T.snr_dB(T.satelliteID==proposed); end
            [~,f,done]=env.stepSatelliteID(selected);
            handovers=handovers+f.handover; blockedCount=blockedCount+blocked;
            k=k+1; logs(k,:)=[f.startTime_s,proposed,selected,f.previousServingSatID, ...
                proposedSNR,oldSNR,blocked,f.handover,f.lostPackets];
        end
        [P,M]=env.results();
        formula=100*(M.generatedPackets-M.receivedPackets)/M.generatedPackets;
        verified=100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets;
        assert(M.pendingPackets==0 && abs(formula-verified)<1e-10 && ...
            abs(formula-M.packetLossRatio)<1e-10,'GSL:HysteresisAccounting');
        row=table(repeat,packetSeed,snrSeed,margin,M.generatedPackets,M.receivedPackets, ...
            M.lostPackets,M.packetLossRatio,M.maxConsecutiveLoss,M.onTimeDeliveryRate_pct, ...
            handovers,M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets, ...
            M.latePackets,blockedCount,verified,'VariableNames',{'repeat','packetSeed','snrSeed', ...
            'margin_dB','generated','received','lost','loss_pct','maxConsecutiveLoss', ...
            'onTime_pct','handovers','phyLoss','handoverLoss','outageLoss','late','blockedSwitches','verifiedLoss_pct'});
        raw=[raw;row]; %#ok<AGROW>
        stem=sprintf('repeat_%02d_margin_%.1f',repeat,margin);
        decisions=array2table(logs,'VariableNames',{'time_s','proposedID','selectedID', ...
            'previousID','proposedSNR_dB','previousSNR_dB','blocked','handover','lostPackets'});
        writetable(decisions,fullfile(outDir,[stem '_decisions.csv']));
        if repeat==1
            writetable(P,fullfile(outDir,[stem '_packets.csv']));
            writetable(M.lossRuns,fullfile(outDir,[stem '_loss_runs.csv']));
        end
        writetable(raw,fullfile(outDir,'runs.csv'));
        fprintf('Run %d/%d | %.1f dB | loss %.4f%% | max run %d | on-time %.4f%% | HO %d\n', ...
            repeat,numel(seeds),margin,M.packetLossRatio,M.maxConsecutiveLoss,M.onTimeDeliveryRate_pct,handovers);
    end
end
summary=table(); paired=table(); fields={'loss_pct','maxConsecutiveLoss','onTime_pct','handovers'};
for margin=margins
    subset=raw(raw.margin_dB==margin,:); base=raw(raw.margin_dB==0,:);
    row=table(margin,height(subset),'VariableNames',{'margin_dB','repeats'});
    diffRow=table(margin,'VariableNames',{'margin_dB'});
    for j=1:numel(fields)
        name=fields{j}; values=subset.(name);
        row.([name '_mean'])=mean(values); row.([name '_std'])=std(values);
        delta=values-base.(name);
        diffRow.([name '_deltaMean'])=mean(delta); diffRow.([name '_deltaStd'])=std(delta);
    end
    summary=[summary;row]; paired=[paired;diffRow]; %#ok<AGROW>
end
writetable(summary,fullfile(outDir,'summary.csv'));
writetable(paired,fullfile(outDir,'paired_changes_vs_no_gate.csv'));
f=figure('Name','GSL DDQN hysteresis comparison','Color','w','Position',[100 100 1100 700]);
tiledlayout(2,2);
labels={'Packet loss [%]','Maximum consecutive loss [packets]','On-time delivery [%]','Handovers'};
for j=1:numel(fields)
    nexttile; name=fields{j};
    errorbar(margins,summary.([name '_mean']),summary.([name '_std']),'o-','LineWidth',1.4);
    xticks(margins); xlabel('Hysteresis margin [dB]; 0 = gate off'); ylabel(labels{j}); grid on;
end
sgtitle(sprintf('Frozen DDQN | %d paired runs | %d s | mean +/- sample SD | attenuation 8 dB',numel(seeds),CFG.duration_s));
exportgraphics(f,fullfile(outDir,'comparison.png'),'Resolution',160);
savefig(f,fullfile(outDir,'comparison.fig'));
R=struct('raw',raw,'summary',summary,'pairedChanges',paired,'config',CFG, ...
    'modelPath',modelPath,'seeds',seeds,'margins_dB',margins,'outputDir',outDir);
save(fullfile(outDir,'comparison.mat'),'R','-v7');
disp(summary); fprintf('Saved to: %s\n',outDir);
end
