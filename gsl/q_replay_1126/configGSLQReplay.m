function O=configGSLQReplay(mode)
if nargin<1,mode='prioritized';end
assert(ismember(mode,{'uniform','prioritized'}));
O=configGSLTrendDDQN();O.replayMode=mode;
O.priorityAlpha=.6;O.priorityBetaStart=.4;O.priorityEpsilon=1e-5;
O.priorityBetaUpdates=7437; % fixed before experiments; 100-episode update budget
O.root=fileparts(mfilename('fullpath'));O.resultRoot=fullfile(O.root,['results_' mode]);
% Diagnostics only: PER >= .9 defines a reported regime, not a sampling cutoff.
% Priority is abs(TD error)+epsilon across ALL transitions, with IS correction.
end
