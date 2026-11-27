function T=open_saved_gsl_counterfactual(show)
% Diagnostic results only; no training and no resimulation.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));T=readtable(fullfile(here,'results','cases.csv'));
vis='off';if show,vis='on';end
f=figure('Visible',vis,'Color','w','Name','GSL maximum burst - counterfactual diagnosis','Position',[50 40 1350 850]);
t=tiledlayout(f,2,2,'Padding','compact','TileSpacing','compact');
for n=[1 3 5]
    A=T(T.nStep==n,:);ax=nexttile(t);plot(ax,A.repeat,A.originalMaxRun,'-ob','LineWidth',1.4);hold(ax,'on');
    plot(ax,A.repeat,A.counterfactualGlobalMax,'-s','Color',[.9 .45 .1],'LineWidth',1.3);
    plot(ax,A.repeat,A.optimisticGlobalMax,'--k','LineWidth',1.4);grid(ax,'on');xlabel(ax,'Repeat');ylabel(ax,'Maximum consecutive loss (packets)');
    title(ax,sprintf('%d-step DDQN: same frozen policy after one forced choice',n));
    if n==1,legend(ax,{'Original','Hindsight intervention','Optimistic floor (no HO)'},'Location','northwest');end
end
ax=nexttile(t);M=zeros(3,3);
for k=1:3,ns=[1 3 5];A=T(T.nStep==ns(k),:);M(k,:)=[mean(A.originalMaxRun) mean(A.counterfactualGlobalMax) mean(A.optimisticGlobalMax)];end
bar(ax,M);xticklabels(ax,{'1-step','3-step','5-step'});ylabel(ax,'Mean maximum loss (packets)');grid(ax,'on');
title(ax,'Mean over 10 paired seeds');legend(ax,{'Original','Hindsight intervention','Optimistic floor'},'Location','northwest');
title(t,{'6x11 | 6 dB | 30 frozen runs, 5338 action branches', ...
    'Hindsight + shared packet draws: diagnostic bounds, NOT a deployable policy performance'});
exportgraphics(f,fullfile(here,'counterfactual_comparison.png'),'Resolution',150);savefig(f,fullfile(here,'counterfactual_comparison.fig'));
if ~show,close(f);end
end
