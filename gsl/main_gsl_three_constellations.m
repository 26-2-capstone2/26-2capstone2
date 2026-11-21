function R=main_gsl_three_constellations(mode)
% GS -> first satellite only: 6x11 / 20x20 / 36x36 comparison and playback.
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'three_constellations'));
R=gslThreeMain(mode);
end
