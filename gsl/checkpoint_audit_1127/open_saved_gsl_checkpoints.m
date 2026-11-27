function S=open_saved_gsl_checkpoints(show)
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));S=readtable(fullfile(here,'results/summary.csv'));F=readtable(fullfile(here,'results/fixed_state_summary.csv'));
v='off';if show,v='on';end
f=figure('Visible',v,'Color','w','Name','GSL saved training checkpoints - frozen evaluation','Position',[40 40 1400 850]);
t=tiledlayout(f,2,3,'Padding','compact','TileSpacing','compact');
fields={'loss_pct','maxLossRun','onTime_pct','handovers','discountedStartReturn'};
labels={'Packet loss (%)','Mean maximum consecutive loss','On-time delivery (%)','Handovers','Sampled discounted return from start'};
for k=1:5
    ax=nexttile(t);T=S(strcmp(S.metric,fields{k}),:);errorbar(ax,T.episode,T.mean,T.sampleSD,'-o','LineWidth',1.4,'MarkerSize',4);grid(ax,'on');
    xlabel(ax,'Training episodes (saved model)');ylabel(ax,labels{k});
    if k==2,hold(ax,'on');yline(ax,35.3,'--k','Optimistic floor mean = 35.3');end
end
ax=nexttile(t);plot(ax,F.episode,F.changedChoice_pct,'-o','LineWidth',1.4);grid(ax,'on');xlabel(ax,'Training episodes');ylabel(ax,'Different choices on SAME 100-model states (%)');
title(t,{'6x11 | 6 dB | 100..1000: ONE training trajectory, frozen evaluation on same 10 seeds', ...
    'No new training, epsilon=0 | error bars: sample SD across evaluation seeds, not training runs'});
exportgraphics(f,fullfile(here,'checkpoint_comparison.png'),'Resolution',150);savefig(f,fullfile(here,'checkpoint_comparison.fig'));
if ~show,close(f);end
end
