function R=main_gsl_q_replay()
% Display saved comparison and packet replay; never starts training.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'q_replay_1126'));
R=open_saved_gsl_q_replay();
if isfile(fullfile(root,'q_replay_1126','validation_new_seeds','runs.csv'))
    plot_gsl_q_replay_validation(true);
end
end
