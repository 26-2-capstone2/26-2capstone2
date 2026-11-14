function f=plotGSLLinkDiagnostics(D,f)
% Reuse this figure when the main environment attenuation slider changes.
if nargin<2 || isempty(f) || ~isgraphics(f)
    f=figure('Name','GSL Candidate SNR and Availability','Color','w', ...
        'Position',[100 80 1200 820]);
else
    clf(f);
end
T=D.perSecond; M=D.policyComparison; C=D.config;
layout=tiledlayout(f,2,2,'TileSpacing','compact','Padding','compact');
layout.OuterPosition=[0 0 1 .80];
visible=T.visibleCandidateCount>0;
range='No visible candidates';
if any(visible)
    range=sprintf('Visible-candidate SNR %.2f to %.2f dB', ...
        min(T.worstCandidateSNR_dB(visible)),max(T.bestCandidateSNR_dB(visible)));
end
summary=sprintf(['Environment %.1f dB | elevation mask %.1f deg | %s\n' ...
    'Current: loss %.3f%% | on-time %.3f%% | max run %d\n' ...
    'Highest SNR / second: loss %.3f%% | on-time %.3f%% | max run %d\n' ...
    'Forced by no candidate or all PER=1: %d packets | longest forced run %d\n' ...
    'PER=1 follows the current PHY model. Highest-SNR selection includes switching losses.'], ...
    D.environmentLoss_dB,C.minElevation_deg,range,M.loss_pct(1),M.onTime_pct(1), ...
    M.maxConsecutiveLoss(1),M.loss_pct(2),M.onTime_pct(2),M.maxConsecutiveLoss(2), ...
    D.unavoidablePackets,D.unavoidableMaxRun);
annotation(f,'textbox',[.02 .82 .96 .16],'String',summary, ...
    'EdgeColor','none','FontSize',11,'Interpreter','none');
a=nexttile(layout);
stairs(a,T.time_s,T.aboveHorizonCount,'Color',[.6 .6 .6]); hold(a,'on');
stairs(a,T.time_s,T.visibleCandidateCount,'b','LineWidth',1.2);
xlabel(a,'Time [s]'); ylabel(a,'Satellites'); title(a,'Visible candidate count');
legend(a,{'Above horizon','Pass elevation mask'},'Location','best'); grid(a,'on');
a=nexttile(layout);
plot(a,T.time_s,T.bestCandidateSNR_dB,'g','LineWidth',1.2); hold(a,'on');
plot(a,T.time_s,T.selectedSNR_dB,'b');
plot(a,T.time_s,T.worstCandidateSNR_dB,'Color',[.7 .4 .2]);
xlabel(a,'Time [s]'); ylabel(a,'SNR [dB]'); title(a,'SNR of visible candidates');
legend(a,{'Best candidate','Current selection','Worst candidate'},'Location','best'); grid(a,'on');
a=nexttile(layout);
labels=["NO_VISIBLE_CANDIDATE","ALL_CANDIDATES_PER_ONE", ...
    "SOME_CANDIDATE_PER_BELOW_ONE","UNRESOLVED_PHY"];
[~,regime]=ismember(T.regime,labels);
stairs(a,T.time_s,regime,'LineWidth',1.3);
yticks(a,1:4); yticklabels(a,{'No candidate','All PER=1','Some PER<1','Unresolved'});
ylim(a,[.7 4.3]); xlabel(a,'Time [s]'); title(a,'Can satellite selection help?'); grid(a,'on');
a=nexttile(layout);
bar(a,[M.phyLoss M.handoverLoss M.outageLoss],'stacked');
xticks(a,1:2); xticklabels(a,{'Current','Highest SNR'});
ylabel(a,'Lost packets'); title(a,'Loss causes');
legend(a,{'PHY','Handover','No candidate'},'Location','best'); grid(a,'on');
end
