root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
O=configGSLQReplay('prioritized');R=run_gsl_q_replay(O);
disp('PRIORITIZED REPLAY PILOT COMPLETE; REWARD/STATE/ACTION/PHY UNCHANGED.');
