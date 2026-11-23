function R=gslTrendMain(mode)
if nargin<1,mode='view';end
O=configGSLTrendDDQN();latest=fullfile(O.resultRoot,'latest_result.txt');
if strcmp(mode,'run')||~isfile(latest)
    R=run_gsl_trend_ddqn(O);
else
    folder=strtrim(fileread(latest));S=load(fullfile(O.resultRoot,folder,'study.mat'),'R');R=S.R;
    R.outputDir=fullfile(O.resultRoot,folder);
end
plotGSLTrendResults(R,true);R.viewer=GSLTrendResultViewer(R);
fprintf('DDQN ONLY: 6x11, 6 dB, trained 100 episodes, evaluated on 10 held-out seeds.\n%s\n',R.outputDir);
end
