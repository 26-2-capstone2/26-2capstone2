function R=gslPairedMain(mode)
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));resultRoot=fullfile(root,'results_baseline_paired');
latest=fullfile(resultRoot,'latest_result.txt');
if strcmp(mode,'run')||~isfile(latest)
    R=run_gsl_baseline_paired();
else
    name=strtrim(fileread(latest));out=fullfile(resultRoot,name);
    S=load(fullfile(out,'comparison.mat'),'R');R=S.R;R.outputDir=out;
end
plotGSLPairedComparison(R,true);
fprintf('Baseline: ZERO training, 10 evaluations paired to the existing DDQN tests.\n');
disp(R.comparison);fprintf('All logs and report: %s\n',R.outputDir);
end
