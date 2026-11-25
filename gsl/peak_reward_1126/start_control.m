root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),fullfile(root,'q_context_1126'));
addpath(fileparts(mfilename('fullpath')));O=configGSLPeakReward('control');R=run_gsl_peak_reward(O);
