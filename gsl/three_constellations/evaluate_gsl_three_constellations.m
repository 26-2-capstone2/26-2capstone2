function [runs,manifest]=evaluate_gsl_three_constellations(O,geometries,configs,agent,out)
policies=["MaxSNR","MaxSNR_Hysteresis","DDQN"]; runs=table();manifest=table();
before=agent.updateCount;
for k=1:3
    for repeat=1:numel(O.evaluationSeeds)
        seed=O.evaluationSeeds(repeat);
        for policy=policies
            env=GSLSelectionEpisode(configs{k},geometries{k},O,seed);
            done=false;
            while ~done
                S=env.observe(); index=selectGSLThreeAction(S,policy,O,agent);
                id=0;if index>0,id=S.ids(index);end
                [~,~,done]=env.step(id);
            end
            [P,M,L]=env.results();
            if policy=="MaxSNR"
                visible=env.geometry.isVisible(1:configs{k}.duration_s,:);
                [rr,cc]=find(visible); index=sub2ind(size(env.snr),rr,cc);
                G=env.geometry;
                candidates=table(G.time_s(rr),cc,G.planeIndex(cc),G.satelliteInPlane(cc), ...
                    G.planeIndex(cc)+1,G.satelliteInPlane(cc)+1,env.snr(index), ...
                    G.elevation_deg(index),env.per(index), ...
                    'VariableNames',{'time_s','satellite_id','p_zero_based','s_zero_based', ...
                    'p','s','snr_dB','elevation_deg','phyPER'});
                candidates=sortrows(candidates,{'time_s','snr_dB'},{'ascend','descend'});
                gridFolder=fullfile(out,sprintf('grid_%dx%d',O.sizes(k,1),O.sizes(k,2)));
                if ~isfolder(gridFolder),mkdir(gridFolder);end
                writetable(candidates,fullfile(gridFolder,sprintf('repeat_%02d_candidates.csv',repeat)));
            end
            row=table(O.sizes(k,1),O.sizes(k,2),policy,repeat,seed,M.generatedPackets, ...
                M.receivedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
                M.maxConsecutiveLoss,sum(env.handovers),M.phyLossPackets,M.handoverLossPackets, ...
                M.outageLossPackets,M.latePackets,M.pendingPackets, ...
                100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets, ...
                'VariableNames',{'planes','satellitesPerPlane','policy','repeat','seed','generated', ...
                'received','lost','loss_pct','onTime_pct','maxLossRun','handovers','phyLoss', ...
                'handoverLoss','outageLoss','late','pending','verifiedLoss_pct'});
            runs=[runs;row]; %#ok<AGROW>
            folder=fullfile(out,sprintf('grid_%dx%d',O.sizes(k,1),O.sizes(k,2)),char(policy));
            if ~isfolder(folder),mkdir(folder);end
            stem=sprintf('repeat_%02d',repeat);
            packetFile=fullfile(folder,[stem '_packets.csv']);
            writetable(P,packetFile); writetable(M.lossRuns,fullfile(folder,[stem '_loss_runs.csv']));
            writetable(L,fullfile(folder,[stem '_decisions.csv']));
            % ISL interface: SUCCESS only, including late GSL arrivals, original ID/time.
            E=P(P.received==1,{'packetID','generationTime_s','arrivalTime_s','destinationSatelliteID', ...
                'destinationPlaneIndex','destinationSatelliteInPlane','onTime','snr_dB'});
            E.Properties.VariableNames={'packet_id','generation_time_s','isl_entry_time_s','satellite_id', ...
                'p_zero_based','s_zero_based','gsl_on_time','snr_dB'};
            E.p=E.p_zero_based+1;E.s=E.s_zero_based+1;
            E.packet_size_bytes=repmat(configs{k}.packetSize_bytes,height(E),1);
            E.flow_id=zeros(height(E),1); % main ISL flow is zero-based flow 0
            assert(all(E.isl_entry_time_s>=E.generation_time_s) && numel(unique(E.packet_id))==height(E));
            writetable(E,fullfile(folder,[stem '_isl_input.csv']));
            config=configs{k}; %#ok<NASGU>
            if repeat==1
                preview=struct('P',P,'M',M,'L',L,'config',config, ...
                    'snr',env.snr,'policy',policy,'seed',seed); %#ok<NASGU>
                save(fullfile(folder,'preview.mat'),'preview','-v7.3');
            end
            relativePacket=string(erase(packetFile,[out filesep]));
            entry=table(k,policy,repeat,seed,relativePacket,height(P),height(E), ...
                'VariableNames',{'gridIndex','policy','repeat','seed','packetFile','packetRows','islInputRows'});
            manifest=[manifest;entry]; %#ok<AGROW>
            writetable(runs,fullfile(out,'runs.csv'));writetable(manifest,fullfile(out,'log_manifest.csv'));
            fprintf('EVAL %dx%d | repeat %d/%d | %s | loss %.3f%% | on-time %.3f%% | max run %d | HO %d\n', ...
                O.sizes(k,1),O.sizes(k,2),repeat,numel(O.evaluationSeeds),policy, ...
                M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(env.handovers));
        end
    end
end
assert(agent.updateCount==before,'GSL:EvaluationChangedAgent');
end
