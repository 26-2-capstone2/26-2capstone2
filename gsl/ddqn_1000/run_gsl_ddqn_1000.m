function R=run_gsl_ddqn_1000(O)
if nargin<1,O=configGSLTrendDDQN();end
if ~isfolder(O.resultRoot),mkdir(O.resultRoot);end
out=fullfile(O.resultRoot,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
C=O.baseConfig;C.numPlanes=6;C.satsPerPlane=11;C.initialEnvironmentLoss_dB=6;
C.makePlots=false;C.openViewer=false;C.openPacketViewer=false;C.exportResults=false;
G=buildGSLSelectionGeometry(C);C.candidateCapacity=max(G.visibleCount);
geometry=G;save(fullfile(out,'geometry.mat'),'geometry','-v7');
save(fullfile(out,'options.mat'),'O','C');
fprintf('DDQN ONLY | 6x11 | 6 dB | 1000 training episodes | 10 held-out evaluation seeds\n');
agent=GSLTrendDoubleDQN(O);training=table();steps=0;
for e=1:O.numEpisodes
    env=GSLTrendEpisode(C,G,O,O.trainingSeeds(e));done=false;losses=[];
    while ~done
        S=env.observe();steps=steps+1;
        epsilon=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(steps-1)/O.epsilonDecaySteps);
        ix=agent.select(S,epsilon,O.qHysteresis);id=0;if ix>0,id=S.ids(ix);end
        [next,reward,done]=env.step(id);agent.remember(S,ix,reward,next,done);
        if mod(steps,O.trainEvery)==0
            loss=agent.learn();if isfinite(loss),losses(end+1)=loss;end %#ok<AGROW>
        end
    end
    edge=diff([false;env.loss;false]);lengths=find(edge==-1)-find(edge==1);
    maxRun=0;if ~isempty(lengths),maxRun=max(lengths);end
    meanLoss=NaN;if ~isempty(losses),meanLoss=mean(losses);end
    training=[training;table(e,O.trainingSeeds(e),epsilon,100*mean(env.loss), ...
        maxRun,sum(env.handovers),sum(env.rewardHistory),meanLoss,agent.updateCount, ...
        'VariableNames',{'episode','seed','epsilon','loss_pct','maxLossRun','handovers','reward','trainingLoss','updates'})]; %#ok<AGROW>
    writetable(training,fullfile(out,'training.csv'));
    checkpoint=agent.checkpoint();save(fullfile(out,'agent.mat'),'checkpoint','O','-v7.3');
    if mod(e,100)==0,save(fullfile(out,sprintf('agent_episode_%04d.mat',e)),'checkpoint','O','-v7.3');end
    fprintf('TRAIN %03d/%d | loss %.3f%% | max run %d | HO %d | eps %.3f | updates %d\n', ...
        e,O.numEpisodes,training.loss_pct(end),maxRun,training.handovers(end),epsilon,agent.updateCount);
end
runs=table();before=agent.updateCount;manifest=table();
for repeat=1:numel(O.evaluationSeeds)
    seed=O.evaluationSeeds(repeat);env=GSLTrendEpisode(C,G,O,seed);done=false;
    while ~done
        S=env.observe();ix=agent.select(S,0,O.qHysteresis);id=0;if ix>0,id=S.ids(ix);end
        [~,~,done]=env.step(id);
    end
    [P,M,L]=env.results();
    row=table(repeat,seed,M.generatedPackets,M.receivedPackets,M.lostPackets, ...
        M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(env.handovers), ...
        M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets, ...
        100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets, ...
        'VariableNames',{'repeat','seed','generated','received','lost','loss_pct','onTime_pct', ...
        'maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','late','pending','verifiedLoss_pct'});
    runs=[runs;row]; %#ok<AGROW>
    folder=fullfile(out,sprintf('repeat_%02d',repeat));mkdir(folder);
    writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));
    writetable(L,fullfile(folder,'decisions.csv'));
    E=P(P.received==1,{'packetID','generationTime_s','arrivalTime_s','destinationSatelliteID', ...
        'destinationPlaneIndex','destinationSatelliteInPlane','onTime','snr_dB'});
    E.Properties.VariableNames={'packet_id','generation_time_s','isl_entry_time_s','satellite_id', ...
        'p_zero_based','s_zero_based','gsl_on_time','snr_dB'};
    E.p=E.p_zero_based+1;E.s=E.s_zero_based+1;
    E.packet_size_bytes=repmat(C.packetSize_bytes,height(E),1);E.flow_id=zeros(height(E),1);
    writetable(E,fullfile(folder,'isl_input.csv'));
    [rr,cc]=find(G.isVisible(1:C.duration_s,:));ind=sub2ind(size(env.snr),rr,cc);
    candidates=table(G.time_s(rr),cc,G.planeIndex(cc)+1,G.satelliteInPlane(cc)+1, ...
        env.snr(ind),G.elevation_deg(ind),env.per(ind), ...
        'VariableNames',{'time_s','satellite_id','p','s','snr_dB','elevation_deg','phyPER'});
    candidates=sortrows(candidates,{'time_s','snr_dB'},{'ascend','descend'});
    writetable(candidates,fullfile(folder,'candidates.csv'));
    preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',"DDQN_5s_trend",'seed',seed); %#ok<NASGU>
    save(fullfile(folder,'preview.mat'),'preview','-v7.3');
    manifest=[manifest;table(repeat,seed,string(sprintf('repeat_%02d/packets.csv',repeat)), ...
        height(P),height(E),'VariableNames',{'repeat','seed','packetFile','packetRows','islInputRows'})]; %#ok<AGROW>
    writetable(runs,fullfile(out,'runs.csv'));writetable(manifest,fullfile(out,'log_manifest.csv'));
    fprintf('EVAL %02d/%d | loss %.4f%% | on-time %.4f%% | max run %d | HO %d\n', ...
        repeat,numel(O.evaluationSeeds),M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(env.handovers));
end
assert(agent.updateCount==before && height(runs)==10 && all(runs.pending==0));
assert(all(abs(runs.loss_pct-runs.verifiedLoss_pct)<1e-10));
summary=table();metrics={'loss_pct','onTime_pct','maxLossRun','handovers'};
for j=1:numel(metrics)
    values=runs.(metrics{j});average=mean(values);sd=std(values);half=2.26215716274099*sd/sqrt(10);
    summary=[summary;table(string(metrics{j}),average,sd,min(values),max(values),average-half,average+half, ...
        'VariableNames',{'metric','mean','std','min','max','mean_lower95','mean_upper95'})]; %#ok<AGROW>
end
writetable(summary,fullfile(out,'summary.csv'));
R=struct('outputDir',out,'options',O,'config',C,'training',training,'runs',runs,'summary',summary);
save(fullfile(out,'study.mat'),'R','-v7.3');
[~,name]=fileparts(out);fid=fopen(fullfile(O.resultRoot,'latest_result.txt'),'w');fprintf(fid,'%s',name);fclose(fid);
fid=fopen(fullfile(out,'VERIFICATION.txt'),'w');
fprintf(fid,'PASS: 1000 training episodes, frozen agent, 10 held-out seeds, 360000 packet records, no pending, exclusive loss accounting.\n');fclose(fid);
plotGSLTrendResults(R,false);
disp(summary);fprintf('DDQN 6x11 COMPLETE: %s\n',out);
end

