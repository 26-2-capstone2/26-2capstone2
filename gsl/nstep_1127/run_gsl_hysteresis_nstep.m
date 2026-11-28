function runs=run_gsl_hysteresis_nstep()
root=setupGSLNStep();O=configGSLNStep(1);p=fullfile(root,'ddqn_6x11/results_ddqn_6x11/20261123_160855_135');
D=load(fullfile(p,'study.mat'),'R');C=configGSLToolboxPHY(D.R.config);D=load(fullfile(p,'geometry.mat'),'geometry');G=D.geometry;
here=fileparts(mfilename('fullpath'));out=fullfile(here,'results_hysteresis');if ~isfolder(out),mkdir(out);end
geometry=G;save(fullfile(out,'geometry.mat'),'geometry');runs=table();
for h=O.hysteresisMargins_dB
    for repeat=1:10
        seed=O.evaluationSeeds(repeat);env=GSLTrendEpisode(C,G,O,seed);blocks=0;trace=table();
        for t=1:C.duration_s
            S=env.observe();ix=0;old=find(S.features(4,:)>0,1);gap=NaN;blocked=false;
            if ~isempty(S.ids)
                [~,ix]=max(S.snr);
                if ~isempty(old)
                    gap=S.snr(ix)-S.snr(old);
                    if gap<h,blocked=ix~=old;ix=old;end
                end
            end
            id=0;if ix>0,id=S.ids(ix);end
            env.step(id);blocks=blocks+blocked;
            trace=[trace;table(t-1,id,gap,blocked,'VariableNames',{'time_s','satelliteID','bestMinusServingSNR_dB','blockedByMargin'})]; %#ok<AGROW>
        end
        [P,M,L]=env.results();folder=fullfile(out,sprintf('h%03d_repeat_%02d',round(h*100),repeat));mkdir(folder);
        writetable(P,fullfile(folder,'packets.csv'));writetable(M.lossRuns,fullfile(folder,'loss_runs.csv'));writetable(L,fullfile(folder,'decisions.csv'));writetable(trace,fullfile(folder,'margin_trace.csv'));
        preview=struct('P',P,'M',M,'L',L,'config',C,'snr',env.snr,'policy',sprintf('MaxSNR_H%.1f',h),'seed',seed);save(fullfile(folder,'preview.mat'),'preview','-v7.3');
        row=table(h,repeat,seed,M.generatedPackets,M.receivedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
            M.maxConsecutiveLoss,sum(env.handovers),M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.latePackets,M.pendingPackets,blocks, ...
            'VariableNames',{'hysteresis_dB','repeat','seed','generated','received','lost','loss_pct','onTime_pct','maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','late','pending','marginBlocks'});
        runs=[runs;row];writetable(runs,fullfile(out,'runs.csv')); %#ok<AGROW>
        fprintf('HYSTERESIS %.1f dB %02d/10 | loss %.4f%% | max %d | HO %d\n',h,repeat,M.packetLossRatio,M.maxConsecutiveLoss,sum(env.handovers));
    end
end
save(fullfile(out,'study.mat'),'runs','C','O','-v7.3');
end
