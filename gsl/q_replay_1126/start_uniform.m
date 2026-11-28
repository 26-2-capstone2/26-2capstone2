root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'));
here=fileparts(mfilename('fullpath'));addpath(here);
O=configGSLQReplay('uniform');R=run_gsl_q_replay(O);
source=fullfile(root,'ddqn_6x11','results_ddqn_6x11','20261123_160855_135');
% Compare file contents, not table import metadata carrying different paths.
assert(strcmp(fileread(fullfile(source,'training.csv')),fileread(fullfile(R.outputDir,'training.csv'))),'Original training metrics changed');
assert(strcmp(fileread(fullfile(source,'runs.csv')),fileread(fullfile(R.outputDir,'runs.csv'))),'Original evaluation metrics changed');
disp('INSTRUMENTED UNIFORM BASELINE EXACTLY REPRODUCES ORIGINAL 100-EPISODE EXPERIMENT.');
