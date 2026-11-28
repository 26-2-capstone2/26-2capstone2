function R=run_gsl_static_front(seed,C)
if nargin<2,C=configGSLStaticFront();end
if nargin<1,seed=C.staticDefaultEpisodeSeed;end
[env,C,G,O]=createGSLStaticFrontEpisode(seed,C);
out=fullfile(C.outputDir,sprintf('seed_%d',seed));if ~isfolder(out),mkdir(out);end
C.outputDir=out;
for t=1:C.duration_s
    S=env.observe();id=0;
    if ~isempty(S.ids)
        [~,j]=max(S.snr);old=find(S.features(4,:)>0,1);
        if ~isempty(old)&&S.snr(j)-S.snr(old)<C.staticBaselineHysteresis_dB,j=old;end
        id=S.ids(j);
    end
    env.step(id);
end
[P,M,L]=env.results();
% The legacy packet evaluator only adds grid indices for moving_grid.
% Derive the same plane-major mapping explicitly for this new geometry.
P.destinationPlaneIndex=nan(height(P),1);P.destinationSatelliteInPlane=nan(height(P),1);
valid=P.destinationSatelliteID>0;
P.destinationPlaneIndex(valid)=G.planeIndex(P.destinationSatelliteID(valid));
P.destinationSatelliteInPlane(valid)=G.satelliteInPlane(P.destinationSatelliteID(valid));
R=struct('config',C,'geometry',G,'options',O,'seed',seed,'packetTable',P,'packetMetrics',M,'linkState',L,'snr',env.snr,'per',env.per, ...
    'policy',sprintf('MaxSNR + %.1f dB (environment demo, NOT new DDQN)',C.staticBaselineHysteresis_dB),'outputDir',out);
initial=SNRTable(R,1);R.initialCandidates=initial;
if C.exportResults
    writetable(G.staticSatellites,fullfile(out,'static_satellites.csv'));writetable(initial,fullfile(out,'initial_candidates.csv'));
    writetable(P,fullfile(out,'packets.csv'));writetable(L,fullfile(out,'decisions.csv'));writetable(M.lossRuns,fullfile(out,'loss_runs.csv'));
    [rr,cc]=find(G.isVisible(1:C.duration_s,:));ix=sub2ind(size(env.snr),rr,cc);
    candidates=table(G.time_s(rr),cc,G.planeIndex(cc)+1,G.satelliteInPlane(cc)+1,env.snr(ix),G.elevation_deg(ix),env.per(ix), ...
        'VariableNames',{'time_s','satelliteID','row','column','snr_dB','elevation_deg','PER'});writetable(candidates,fullfile(out,'candidates.csv'));
    E=P(P.received==1,{'packetID','generationTime_s','arrivalTime_s','destinationSatelliteID','destinationPlaneIndex','destinationSatelliteInPlane','onTime','snr_dB'});
    E.Properties.VariableNames={'packet_id','generation_time_s','isl_entry_time_s','satellite_id','p_zero_based','s_zero_based','gsl_on_time','snr_dB'};
    E.p=E.p_zero_based+1;E.s=E.s_zero_based+1;E.packet_size_bytes=repmat(C.packetSize_bytes,height(E),1);writetable(E,fullfile(out,'isl_input.csv'));
    fid=fopen(fullfile(out,'environment.json'),'w','n','UTF-8');fprintf(fid,'%s',jsonencode(G.layout,'PrettyPrint',true));fclose(fid);
    save(fullfile(out,'result.mat'),'R','-v7.3');
    root=fileparts(out);fid=fopen(fullfile(root,'latest_result.txt'),'w');fprintf(fid,'seed_%d',seed);fclose(fid);
end
fprintf('STATIC FRONT GRID | %dx%d | seed %d | heading %.1f deg | positions fixed for %d s\n',C.numPlanes,C.satsPerPlane,seed,G.layout.heading_deg,C.duration_s);
fprintf('GS near column 1 | grid center along %.1f km | visible %d | SNR std %.1f dB, correlation %.1f s\n',G.layout.centerAlongCoordinate_m/1000,G.visibleCount(1),C.snrRandomStd_dB,C.snrCorrelation_s);
fprintf('DEMO POLICY: %s\nGenerated %d | received %d | loss %.4f%% | max run %d | HO %d\n',R.policy,M.generatedPackets,M.receivedPackets,M.packetLossRatio,M.maxConsecutiveLoss,sum(env.handovers));
end
function T=SNRTable(R,t)
ids=find(R.geometry.isVisible(t,:)).';T=R.geometry.staticSatellites(ids,:);T.snr_dB=R.snr(t,ids).';T.PER=R.per(t,ids).';T=sortrows(T,'snr_dB','descend');
end
