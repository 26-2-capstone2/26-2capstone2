function R=main_gsl_ddqn_1000()
% Run to immediately display saved training, evaluation and packet results.
root=fileparts(mfilename('fullpath'));
addpath(fullfile(root,'ddqn_1000'));
R=open_saved_gsl_ddqn_1000(true);
end
