function f=plot_gsl_q_replay_validation(show)
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));D=readtable(fullfile(here,'validation_new_seeds','runs.csv'));
v='off';if show,v='on';end
f=figure('Name','Q replay - New held-out seed evaluation','Color','w','Visible',v,'Position',[60 60 1200 800]);
t=tiledlayout(f,2,2);fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Max consecutive loss (packets)','On-time delivery (%)','Handovers'};
modes={'uniform','prioritized'};
for j=1:4
    means=zeros(1,2);sds=means;
    for k=1:2,z=D.(fields{j})(strcmp(D.mode,modes{k}));means(k)=mean(z);sds(k)=std(z);end
    ax=nexttile(t);b=bar(ax,1:2,means,'FaceColor','flat');b.CData=[.25 .46 .75;.92 .44 .12];hold(ax,'on');
    errorbar(ax,1:2,means,sds,'k.');xticks(ax,1:2);xticklabels(ax,{'Original uniform','TD-prioritized'});
    ylabel(ax,labels{j});grid(ax,'on');ylim(ax,[0 1.22*max(means+sds)]);
    for k=1:2,text(ax,k,means(k)+sds(k),sprintf(' %.3f',means(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');end
end
title(t,{'Q learning pilot | 6x11 | 6 dB | 100 training episodes per method', ...
    '10 NEW paired seeds 20274001-20274010 | mean +/- SD | reward unchanged'});
exportgraphics(f,fullfile(here,'new_seed_comparison.png'),'Resolution',160);savefig(f,fullfile(here,'new_seed_comparison.fig'));
if ~show,close(f);end
end
