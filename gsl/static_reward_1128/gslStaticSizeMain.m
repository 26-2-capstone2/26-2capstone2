function R=gslStaticSizeMain(mode,rows,columns)
% Shared GitHub entry for larger static-grid experiments.
setupStaticReward();O=configGSLStaticReward();O.baseConfig.numPlanes=rows;O.baseConfig.satsPerPlane=columns;
O.rewardDefinitions=O.rewardDefinitions(2);O.evaluationQMargins=.02;
O.maxSNRMargin_dB=0;O.includeElevation=true;O.elevationMargin_deg=4;
O.resultRoot=fullfile(fileparts(which('configGSLStaticReward')),sprintf('results_policy_%dx%d',rows,columns));
if strcmpi(mode,'run')
    R=runStaticRewardStudy(O);
else
    assert(strcmpi(mode,'show'));
    latest=fullfile(O.resultRoot,'latest_result.txt');assert(isfile(latest),'No saved study. Use run to train and evaluate.');
    saved=strtrim(fileread(latest));[~,name]=fileparts(saved);out=fullfile(O.resultRoot,name);
    S=load(fullfile(out,'study.mat'),'R');R=S.R;R.outputDir=out;R.options.resultRoot=O.resultRoot;
    assert(R.options.baseConfig.numPlanes==rows&&R.options.baseConfig.satsPerPlane==columns);
    plotStaticRewardStudy(R);disp(R.summary);
end
end
