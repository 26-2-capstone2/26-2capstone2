function S=main_gsl_checkpoint_comparison()
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'checkpoint_audit_1127'));
S=open_saved_gsl_checkpoints(true);
end
