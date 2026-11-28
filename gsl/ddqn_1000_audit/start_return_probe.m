root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
auditRoot=fullfile(here,'results_burst_audit');
out=fullfile(auditRoot,strtrim(fileread(fullfile(auditRoot,'latest_result.txt'))));
ddqnRoot=fullfile(root,'ddqn_1000','results_ddqn_1000','20261125_184805_356');
T=probe_gsl_1000_returns(ddqnRoot,out);
