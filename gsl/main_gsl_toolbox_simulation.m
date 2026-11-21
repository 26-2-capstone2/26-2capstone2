function R=main_gsl_toolbox_simulation()
% F5: existing 600 s results, environment slider and numbered packet viewer.
CFG=configGSLToolboxPHY();
CFG.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_toolbox_phy','interactive');
R=main_gsl_simulation(CFG);
end
