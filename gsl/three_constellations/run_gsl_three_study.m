function R=run_gsl_three_study(O)
if nargin<1,O=configGSLThreeConstellations();end
if ~isfolder(O.resultRoot),mkdir(O.resultRoot);end
out=fullfile(O.resultRoot,char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));mkdir(out);
save(fullfile(out,'options.mat'),'O');
[G,configs]=prepareGSLThreeGeometries(O);
for k=1:3
    geometry=G{k};config=configs{k}; %#ok<NASGU>
    save(fullfile(out,sprintf('geometry_%dx%d.mat',O.sizes(k,1),O.sizes(k,2))), ...
        'geometry','config','-v7');
    ids=(1:size(geometry.isVisible,2)).';
    T=table(ids,geometry.planeIndex,geometry.satelliteInPlane, ...
        geometry.planeIndex+1,geometry.satelliteInPlane+1, ...
        geometry.positionStartECEF_m(1,:).',geometry.positionStartECEF_m(2,:).', ...
        geometry.positionStartECEF_m(3,:).','VariableNames', ...
        {'satellite_id','p_zero_based','s_zero_based','p','s','x_start_m','y_start_m','z_start_m'});
    writetable(T,fullfile(out,sprintf('satellite_map_%dx%d.csv',O.sizes(k,1),O.sizes(k,2))));
end
[agent,training]=train_gsl_three_ddqn(O,G,configs,out);
[runs,manifest]=evaluate_gsl_three_constellations(O,G,configs,agent,out);
summary=table();policies=["MaxSNR","MaxSNR_Hysteresis","DDQN"];
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
for k=1:3
    for policy=policies
        subset=runs(runs.planes==O.sizes(k,1)&runs.satellitesPerPlane==O.sizes(k,2)&runs.policy==policy,:);
        row=table(string(sprintf('%dx%d',O.sizes(k,1),O.sizes(k,2))),policy,height(subset), ...
            'VariableNames',{'constellation','policy','repeats'});
        for j=1:numel(fields)
            row.([fields{j} '_mean'])=mean(subset.(fields{j}));
            row.([fields{j} '_std'])=std(subset.(fields{j}));
        end
        summary=[summary;row]; %#ok<AGROW>
    end
end
writetable(summary,fullfile(out,'summary.csv'));
assert(height(runs)==3*3*numel(O.evaluationSeeds) && all(runs.pending==0));
assert(all(abs(runs.loss_pct-runs.verifiedLoss_pct)<1e-10));
R=struct('outputDir',out,'summary',summary,'runs',runs,'training',training,'manifest',manifest,'options',O);
save(fullfile(out,'study.mat'),'R','-v7.3');
fid=fopen(fullfile(O.resultRoot,'latest_result.txt'),'w');fprintf(fid,'%s',string(extractAfter(out,[O.resultRoot filesep])));fclose(fid);
plotGSLThreeSummary(R);
fid=fopen(fullfile(out,'VERIFICATION.txt'),'w');
fprintf(fid,'PASS: %d full 600s runs; %d packet records; exclusive cause accounting; frozen test agent; no radius/top-K filter.\n',height(runs),sum(runs.generated));fclose(fid);
disp(summary);fprintf('GSL THREE-CONSTELLATION STUDY COMPLETE: %s\n',out);
end
