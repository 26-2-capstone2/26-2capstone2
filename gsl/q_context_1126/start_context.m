root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
O=configGSLQContext();R=run_gsl_q_context(O);
disp('CANDIDATE CONTEXT PILOT COMPLETE: uniform replay, original reward, one added input only.');
