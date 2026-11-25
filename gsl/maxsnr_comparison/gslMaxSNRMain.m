function R=gslMaxSNRMain(mode)
if nargin<1,mode='view';end
root=fullfile(fileparts(mfilename('fullpath')),'results_maxsnr');latest=fullfile(root,'latest_result.txt');
if strcmp(mode,'run')||~isfile(latest)
    R=run_gsl_maxsnr_comparison();
else
    out=fullfile(root,strtrim(fileread(latest)));S=load(fullfile(out,'comparison.mat'),'R');R=S.R;R.outputDir=out;
end
plotGSLMaxSNRComparison(R,true);disp(R.paired);
fprintf('No learning: Max-SNR evaluated 10 times; original and DDQN results reused.\n%s\n',R.outputDir);
end
