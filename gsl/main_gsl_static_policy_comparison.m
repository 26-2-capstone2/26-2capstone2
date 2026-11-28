function R=main_gsl_static_policy_comparison(mode)
% Static environment: 100-episode quadratic DDQN vs two untrained baselines.
here=fileparts(mfilename('fullpath'));module=fullfile(here,'static_reward_1128');
if isfolder(module),addpath(module);else,addpath(here);end
setupStaticReward();O=configGSLStaticReward();
O.rewardDefinitions=O.rewardDefinitions(2);O.evaluationQMargins=.02;
O.maxSNRMargin_dB=0;O.includeElevation=true;O.elevationMargin_deg=4;
O.resultRoot=fullfile(fileparts(which('configGSLStaticReward')),'results_policy_comparison');
if nargin<1,mode='show';end
if strcmpi(mode,'show')&&isfile(fullfile(O.resultRoot,'latest_result.txt'))
    saved=strtrim(fileread(fullfile(O.resultRoot,'latest_result.txt')));[~,name]=fileparts(saved);
    folder=fullfile(O.resultRoot,name);D=load(fullfile(folder,'study.mat'),'R');R=D.R;
    R.outputDir=folder;R.options.resultRoot=O.resultRoot;plotStaticRewardStudy(R);disp(R.summary);
else
    assert(any(strcmpi(mode,{'show','run'})));R=runStaticRewardStudy(O);
end
end
