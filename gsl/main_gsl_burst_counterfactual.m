function T=main_gsl_burst_counterfactual()
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'burst_counterfactual_1127'));
T=open_saved_gsl_counterfactual(true);
end
