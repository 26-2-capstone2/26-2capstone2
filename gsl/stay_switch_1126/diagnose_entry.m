root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),fullfile(root,'q_context_1126'));
addpath(fileparts(mfilename('fullpath')));T=compare_stay_switch_training();
