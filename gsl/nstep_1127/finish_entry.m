addpath(fileparts(mfilename('fullpath')));setupGSLNStep();verify_saved_experiment();R=open_saved_gsl_nstep(false);
assert(height(R.training)==100&&height(R.runs)==10&&numel(R.options.featureNames)==11);
fprintf('SAVED COMPARISON REOPEN PASS: no training.\n');
