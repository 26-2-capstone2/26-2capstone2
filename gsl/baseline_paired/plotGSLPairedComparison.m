function f=plotGSLPairedComparison(R,show)
if nargin<2,show=true;end
visibility='off';if show,visibility='on';end
f=figure('Visible',visibility,'Color','w','Name','Elevation Baseline vs DDQN - Paired Ten Tests','Position',[60 60 1150 740]);
tiledlayout(f,2,2);fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss [%]','Max consecutive loss [packets]','On-time delivery [%]','Handovers'};
for k=1:4
    nexttile;values=[R.baseline.(fields{k}),R.ddqn.(fields{k})];bar(values);grid on;
    xlabel('Same test seed / repeat');ylabel(labels{k});
    if k==1,legend({'Elevation + 4 deg','DDQN + Q margin 0.02'},'Location','best');end
end
sgtitle('6x11 | 6 dB | same geometry, channel and packet draws | 10 paired tests | GS -> first satellite');
exportgraphics(f,fullfile(R.outputDir,'comparison.png'),'Resolution',160);
g=figure('Visible',visibility,'Color','w','Name','Baseline vs DDQN - Ten Test Means','Position',[80 80 1100 700]);
tiledlayout(g,2,2);
for k=1:4
    nexttile;a=R.baseline.(fields{k});b=R.ddqn.(fields{k});bar([mean(a),mean(b)]);hold on;
    errorbar([1,2],[mean(a),mean(b)],[std(a),std(b)],'k.');grid on;
    xticks([1 2]);xticklabels({'Elevation + 4 deg','DDQN'});ylabel(labels{k});
end
sgtitle('Mean +/- sample SD across 10 paired seeds (not confidence intervals)');
exportgraphics(g,fullfile(R.outputDir,'comparison_means.png'),'Resolution',160);
if ~show,close(f);close(g);end
end
