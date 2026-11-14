function saveGSLLinkDiagnostics(D,C,f)
if ~isfolder(C.outputDir), mkdir(C.outputDir); end
writetable(D.perSecond,fullfile(C.outputDir,'candidate_snr_by_second.csv'));
writetable(D.candidates,fullfile(C.outputDir,'candidate_snr_details.csv'));
writetable(D.regimeSummary,fullfile(C.outputDir,'candidate_regime_summary.csv'));
writetable(D.policyComparison,fullfile(C.outputDir,'candidate_policy_comparison.csv'));
if nargin>=3 && isgraphics(f)
    exportgraphics(f,fullfile(C.outputDir,'candidate_diagnostics.png'),'Resolution',140);
end
end
