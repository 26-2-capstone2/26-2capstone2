function R=main_gsl_static_reward_comparison(mode)
% Default reopens completed full study, otherwise trains 100 episodes per arm.
here=fileparts(mfilename('fullpath'));module=fullfile(here,'static_reward_1128');
if isfolder(module),addpath(module);else,addpath(here);end
setupStaticReward();O=configGSLStaticReward();if nargin<1,mode='show';end
if strcmpi(mode,'smoke')
    O.smoke=true;O.numEpisodes=2;O.trainingSeeds=O.trainingSeeds(1:2);O.evaluationSeeds=O.evaluationSeeds(1:2);
    O.resultRoot=fullfile(O.resultRoot,'smoke');R=runStaticRewardStudy(O);
elseif strcmpi(mode,'show')&&isfile(fullfile(O.resultRoot,'latest_result.txt'))
    folder=strtrim(fileread(fullfile(O.resultRoot,'latest_result.txt')));D=load(fullfile(folder,'study.mat'),'R');R=D.R;plotStaticRewardStudy(R);disp(R.summary);
else
    assert(any(strcmpi(mode,{'show','run'})),'Use show, run, or smoke');R=runStaticRewardStudy(O);
end
end
