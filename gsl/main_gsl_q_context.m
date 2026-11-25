function R=main_gsl_q_context()
% Show stored experiment and packet playback, without retraining.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'q_context_1126'));
R=open_saved_gsl_q_context(true);
end
