function f=plotGSLMaxSNRComparison(R,show)
if nargin<2,show=true;end
visibility='off';if show,visibility='on';end
f=figure('Visible',visibility,'Color','w','Name','Elevation / Max-SNR / DDQN - Ten Test Means','Position',[60 60 1200 760]);
tiledlayout(f,2,2);fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss [%]','Max consecutive loss [packets]','On-time delivery [%]','Handovers'};
for j=1:4
    nexttile;values=[R.baseline.(fields{j}),R.maxsnr.(fields{j}),R.ddqn.(fields{j})];
    bar(mean(values));hold on;errorbar(1:3,mean(values),std(values),'k.');grid on;
    xticks(1:3);xticklabels({'Elevation+4 deg','Max-SNR','DDQN+Q margin'});ylabel(labels{j});
end
sgtitle('6x11 | 6 dB | 10 paired seeds | mean +/- sample SD | GS -> first satellite');
exportgraphics(f,fullfile(R.outputDir,'three_policy_means.png'),'Resolution',160);
g=figure('Visible',visibility,'Color','w','Name','Max-SNR vs DDQN - Paired Ten Tests','Position',[80 80 1150 740]);
tiledlayout(g,2,2);
for j=1:4
    nexttile;bar([R.maxsnr.(fields{j}),R.ddqn.(fields{j})]);grid on;
    xlabel('Same seed / evaluation repeat');ylabel(labels{j});
    if j==1,legend({'Max-SNR (no gate)','DDQN (Q gate 0.02)'},'Location','best');end
end
sgtitle('Same geometry / all-candidate SNR / packet draws / PHY | 10 paired tests');
exportgraphics(g,fullfile(R.outputDir,'maxsnr_vs_ddqn.png'),'Resolution',160);
if ~show,close(f);close(g);end
end
