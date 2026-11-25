root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
verify_gsl_q_replay();
