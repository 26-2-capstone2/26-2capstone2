root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
source=fullfile(root,'ddqn_6x11','results_ddqn_6x11','20261123_160855_135');
base=fullfile(here,'results_uniform');out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
for f={'training.csv','runs.csv'}
    assert(strcmp(fileread(fullfile(source,f{1})),fileread(fullfile(out,f{1}))));
end
fprintf('UNIFORM CONTROL PASS: complete training/evaluation CSV exactly matches original.\n');
plot_gsl_q_replay_validation(false);
set(groot,'DefaultFigureVisible','off');R=open_saved_gsl_q_replay();
assert(height(R.training)==100&&height(R.runs)==10);delete(R.viewer);close all;
fprintf('SAVED REOPEN PASS: comparison and packet viewer load without retraining.\n');
