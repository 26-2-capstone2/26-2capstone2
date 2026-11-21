function R=gslThreeMain(mode)
% Run without arguments to review completed study; 'run' retrains/re-evaluates.
if nargin<1,mode='view';end
O=configGSLThreeConstellations(); latest=fullfile(O.resultRoot,'latest_result.txt');
if strcmp(mode,'run') || ~isfile(latest)
    R=run_gsl_three_study(O);
else
    folder=strtrim(fileread(latest)); S=load(fullfile(O.resultRoot,folder,'study.mat'),'R');
    R=S.R;R.outputDir=fullfile(O.resultRoot,folder);R.options.root=O.root;
    plotGSLThreeSummary(R);
end
R.viewer=GSLThreeResultViewer(R);
fprintf('Scope: GS -> first satellite ONLY. ISL forwarding is not simulated.\n');
fprintf('Summary and ALL-repeat packet/ISL-input CSV: %s\n',R.outputDir);
end
