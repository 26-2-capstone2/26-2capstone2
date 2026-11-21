function f=plotGSLThreeSummary(R)
S=R.summary; f=figure('Color','w','Name','GSL Three Constellations - Comparison','Position',[80 60 1150 760]);
tiledlayout(f,2,2,'Padding','compact','TileSpacing','compact');
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'GSL packet loss [%]','Maximum consecutive loss [packets]','On-time delivery [%]','Handovers'};
for j=1:4
    nexttile;
    means=reshape(S.([fields{j} '_mean']),3,3).';
    deviations=reshape(S.([fields{j} '_std']),3,3).';
    b=bar(means);hold on;
    for k=1:3,errorbar(b(k).XEndPoints,means(:,k),deviations(:,k),'k.','HandleVisibility','off');end
    xticklabels({'6x11','20x20','36x36'});ylabel(labels{j});grid on;
    if j==1,legend({'Max-SNR','Max-SNR + 0.1 dB','Candidate DDQN + Q margin'},'Location','best');end
end
sgtitle(sprintf('GS -> FIRST SATELLITE ONLY | 8 dB | 600 s | %d paired test seeds | mean +/- sample SD',numel(R.options.evaluationSeeds)));
exportgraphics(f,fullfile(R.outputDir,'comparison.png'),'Resolution',160);
t=R.training; g=figure('Visible','off','Color','w','Name','GSL Candidate DDQN Training','Position',[120 100 1000 450]);
tiledlayout(g,1,2);nexttile;plot(t.episode,t.loss_pct,'o-');grid on;xlabel('Training episode');ylabel('Exploratory packet loss [%]');
nexttile;plot(t.episode,t.reward,'o-');grid on;xlabel('Training episode');ylabel('Episode reward');
sgtitle('Exploration runs across three grids; training curve is not held-out performance');
exportgraphics(g,fullfile(R.outputDir,'training.png'),'Resolution',160);
close(g);
end
