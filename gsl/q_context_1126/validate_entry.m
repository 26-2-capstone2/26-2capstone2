root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
addpath(fileparts(mfilename('fullpath')));V=evaluate_gsl_context_validation();
