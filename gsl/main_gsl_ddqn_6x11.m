function R=main_gsl_ddqn_6x11(mode)
% 6x11 / 6 dB DDQN: saved ten-test report and packet playback.
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
R=gslTrendMain(mode);
end
