function main_gsl_reward_audit()
% Reopen stored reward-alignment evidence without simulation or training.
root=fileparts(mfilename('fullpath'));addpath(fullfile(root,'reward_audit_1126'));
open_saved_gsl_reward_audit(true);
end
