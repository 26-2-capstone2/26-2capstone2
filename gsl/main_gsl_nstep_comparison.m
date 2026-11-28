function R=main_gsl_nstep_comparison()
% Open saved comparison only, no training.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'nstep_1127'));
R=open_saved_gsl_nstep(true);
end
