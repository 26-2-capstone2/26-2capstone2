function R=main_gsl_burst_audit(mode)
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),fullfile(root,'burst_audit'));
R=gslBurstAuditMain(mode);
end
