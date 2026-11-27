function S=open_saved_gsl_stability(show)
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));S=readtable(fullfile(here,'summary.csv'));vis='off';if show,vis='on';end
f=figure('Visible',vis,'Color','w','Name','GSL one-factor stability pilot - saved results','Position',[40 40 1500 850]);
layout=tiledlayout(f,2,4,'Padding','compact','TileSpacing','compact');
modes={'control','low_lr','large_buffer','soft_target'};fields={'loss_pct','maxLossRun','onTime_pct','handovers'};labels={'Packet loss (%)','Maximum consecutive loss','On-time delivery (%)','Handovers'};
for e=[100 200]
    for j=1:4
        mu=zeros(1,4);sd=mu;
        for k=1:4,row=S(strcmp(S.mode,modes{k})&S.episode==e&strcmp(S.metric,fields{j}),:);mu(k)=row.mean;sd(k)=row.sampleSD;end
        ax=nexttile(layout);b=bar(ax,mu,'FaceColor','flat');b.CData=[.3 .5 .75;.9 .5 .15;.35 .65 .35;.65 .4 .7];hold(ax,'on');errorbar(ax,1:4,mu,sd,'k.');grid(ax,'on');
        xticks(ax,1:4);xticklabels(ax,{'Base','LR','Buffer','Target'});xtickangle(ax,20);ylabel(ax,labels{j});title(ax,sprintf('%d episodes',e));ylim(ax,[0 1.25*max(mu+sd)]);
        for k=1:4,text(ax,k,mu(k)+sd(k),sprintf('%.2f',mu(k)),'HorizontalAlignment','center','VerticalAlignment','bottom','FontSize',9);end
    end
end
title(layout,{'6x11 | 6 dB | same 10 validation seeds | one initialization, one factor per arm', ...
    'Base: LR 3e-4, buffer 20k, hard target 100 | LR: 1e-4 | Buffer: 60k | Target: tau=.01'});
exportgraphics(f,fullfile(here,'stability_comparison.png'),'Resolution',150);savefig(f,fullfile(here,'stability_comparison.fig'));if ~show,close(f);end
end
