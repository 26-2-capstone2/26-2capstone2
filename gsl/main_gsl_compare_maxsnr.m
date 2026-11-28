function R=main_gsl_compare_maxsnr(mode)
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));addpath(root,fullfile(root,'three_constellations'),fullfile(root,'maxsnr_comparison'));
R=gslMaxSNRMain(mode);
end
