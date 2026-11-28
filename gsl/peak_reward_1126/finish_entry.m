root=fileparts(fileparts(mfilename('fullpath')));
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),fullfile(root,'q_context_1126'));
addpath(fileparts(mfilename('fullpath')));R=open_saved_gsl_peak_reward(false);
assert(height(R.training)==100&&height(R.runs)==10&&numel(R.options.featureNames)==14);
for repeat=1:10
    T=readtable(fullfile(R.outputDir,sprintf('repeat_%02d',repeat),'objective_trace.csv'));
    assert(sum(T.peakIncrement)==R.runs.maxLossRun(repeat));
    assert(abs(sum(T.reward)+(R.runs.lost(repeat)+.3*R.runs.maxLossRun(repeat))/60)<1e-9);
end
fprintf('SAVED PEAK REWARD REOPEN PASS: 14 inputs, 10 full-episode objectives verified, no retraining.\n');
