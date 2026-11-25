function R=main_gsl_compare_baseline(mode)
if nargin<1,mode='view';end
root=fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'baseline_paired'));
R=gslPairedMain(mode);
end
