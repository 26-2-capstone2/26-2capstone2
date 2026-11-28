root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),fullfile(root,'q_context_1126'),fullfile(root,'stay_switch_1126'));
addpath(fileparts(mfilename('fullpath')));
T=audit_synthetic_reward();R=audit_full_reward_alignment();
