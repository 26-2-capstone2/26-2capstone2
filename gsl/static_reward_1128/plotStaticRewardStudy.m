function f=plotStaticRewardStudy(R)
S=R.summary;f=figure('Name','Static GSL reward comparison','Color','w','Position',[80 80 1400 850]);
tiledlayout(2,2);metrics={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss [%]','Max consecutive loss [packets]','On-time delivery [%]','Handovers'};
names=unique(S.policy,'stable');
for k=1:4
    nexttile;T=S(S.metric==string(metrics{k}),:);[~,ix]=ismember(names,T.policy);T=T(ix,:);
    bar(T.mean);hold on;errorbar(1:height(T),T.mean,T.std,'.k');grid on;
    xticks(1:numel(names));xticklabels(names);xtickangle(20);set(gca,'TickLabelInterpreter','none');ylabel(labels{k});
    title('Mean +/- sample SD (not confidence intervals)');
end
prefix='';if R.options.smoke,prefix='SMOKE TEST ONLY | ';end
sgtitle(sprintf('%sStatic %dx%d | %g dB | %d DDQN training episodes | %d paired evaluation seeds',prefix,R.options.baseConfig.numPlanes,R.options.baseConfig.satsPerPlane,R.options.baseConfig.initialEnvironmentLoss_dB,R.options.numEpisodes,numel(R.options.evaluationSeeds)));
exportgraphics(f,fullfile(R.outputDir,'comparison.png'),'Resolution',140);savefig(f,fullfile(R.outputDir,'comparison.fig'));
end
