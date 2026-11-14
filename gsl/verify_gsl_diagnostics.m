function verify_gsl_diagnostics()
C=configGSL(); C.exportResults=false; C.makePlots=true; C.openPacketViewer=false;
R=main_gsl_simulation(C);
D=R.candidateDiagnostics;
assert(sum(D.regimeSummary.duration_s)==600);
assert(height(D.perSecond)==600);
assert(height(D.candidates)==sum(sum(R.geometry.isVisible(1:end-1,:))));
assert(D.policyComparison.lost(1)==R.packetMetrics.lostPackets);
assert(all(D.policyComparison.lost>=D.unavoidablePackets));
assert(all(D.policyComparison.maxConsecutiveLoss>=D.unavoidableMaxRun));
selected=D.candidates(D.candidates.isSelected,:);
idx=selected.time_s+1;
assert(isequal(selected.snr_dB,R.linkState.snr_dB(idx)));
for t=0:599
    candidates=D.candidates(D.candidates.time_s==t,:);
    if isempty(candidates)
        assert(D.perSecond.regime(t+1)=="NO_VISIBLE_CANDIDATE");
    else
        assert(D.perSecond.bestCandidateSNR_dB(t+1)==max(candidates.snr_dB));
        assert(D.perSecond.worstCandidateSNR_dB(t+1)==min(candidates.snr_dB));
        assert((D.perSecond.regime(t+1)=="ALL_CANDIDATES_PER_ONE")==all(candidates.phyPER==1));
    end
end
f=R.attenuationResultsFigure;
updateGSLAttenuation(f,0);
low=getappdata(f,'GSLCandidateDiagnostics');
assert(low.environmentLoss_dB==0);
assert(low.unavoidablePackets<=D.unavoidablePackets);
assert(max(abs(low.candidates.snr_dB-D.candidates.snr_dB-8))<1e-10);
assert(isequal(low.perSecond.visibleCandidateCount,D.perSecond.visibleCandidateCount));
testDir=fullfile(fileparts(pwd),'gsl_diagnostics_validation');
if ~isfolder(testDir), mkdir(testDir); end
saveConfig=C; saveConfig.outputDir=testDir;
saveGSLLinkDiagnostics(low,saveConfig,getappdata(f,'GSLCandidateDiagnosticsFigure'));
assert(isfile(fullfile(testDir,'candidate_diagnostics.png')));
assert(height(readtable(fullfile(testDir,'candidate_snr_by_second.csv')))==600);
updateGSLAttenuation(f,8);
D=getappdata(f,'GSLCandidateDiagnostics');
saveConfig.outputDir=fullfile(testDir,'loss_8_dB');
saveGSLLinkDiagnostics(D,saveConfig,getappdata(f,'GSLCandidateDiagnosticsFigure'));
disp(D.regimeSummary);
disp(D.policyComparison);
fprintf('Candidate SNR range %.4f to %.4f dB; forced loss %d; forced max run %d\n', ...
    min(D.candidates.snr_dB),max(D.candidates.snr_dB),D.unavoidablePackets,D.unavoidableMaxRun);
disp('PASS full candidate diagnostics, slider updates, paired policy comparison and CSV/PNG export');
end
