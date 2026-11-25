function R=main_gsl_stay_switch()
% Reopen saved comparison and packet outcomes without training.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'stay_switch_1126'));
R=open_saved_gsl_stay_switch(true);
end
