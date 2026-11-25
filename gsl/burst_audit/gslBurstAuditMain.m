function R=gslBurstAuditMain(mode)
if nargin<1,mode='view';end
root=fullfile(fileparts(mfilename('fullpath')),'results_burst_audit');latest=fullfile(root,'latest_result.txt');
if strcmp(mode,'run')||~isfile(latest)
    R=run_gsl_burst_audit();
else
    out=fullfile(root,strtrim(fileread(latest)));S=load(fullfile(out,'audit.mat'),'R');R=S.R;R.outputDir=out;
end
plot_gsl_burst_audit(R.outputDir,true);disp(R.ablation);
fprintf('Frozen network audit: exact replay and no-margin diagnostic; no retraining.\n%s\n',R.outputDir);
end
