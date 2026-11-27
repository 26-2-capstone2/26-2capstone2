function S=main_gsl_stability_comparison()
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'stability_1127'));S=open_saved_gsl_stability(true);
end
