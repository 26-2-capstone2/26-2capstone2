function R=main_gsl_hold_diagnostic(mode,sourceRoot)
% Default opens saved diagnostic. 'run' re-evaluates frozen models; no training.
here=fileparts(mfilename('fullpath'));module=fullfile(here,'hold_diagnostic_1128');
if isfolder(module),addpath(module);else,addpath(here);module=here;end
if nargin<1,mode='show';end
root=fileparts(module);
out=fullfile(module,'results');
if strcmpi(mode,'run')||~isfile(fullfile(out,'diagnostic.mat'))
    assert(any(strcmpi(mode,{'show','run'})));
    if nargin>=2,root=sourceRoot;end
    assert(isfolder(fullfile(root,'6x11','gsl')),'Raw local snapshots required. Use main_gsl_hold_diagnostic(''run'', pathTo1128). GitHub includes saved views, not full packet traces.');
    base=fullfile(root,'6x11','gsl');addpath(base,fullfile(base,'static_front_1127'),fullfile(base,'static_reward_1128'),fullfile(base,'three_constellations'),fullfile(base,'ddqn_6x11'));
    R=runGSLHoldDiagnostic(root,out);
else
    D=load(fullfile(out,'diagnostic.mat'),'R');R=D.R;R.outputDir=out;
end
plotGSLHoldDiagnostic(R);disp(R.summary);disp(R.localSummary);
end
