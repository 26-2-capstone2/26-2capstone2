function R=main_gsl_peak_reward()
% Display saved aligned-reward experiment, never retrain by default.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'peak_reward_1126'));
R=open_saved_gsl_peak_reward(true);
end
