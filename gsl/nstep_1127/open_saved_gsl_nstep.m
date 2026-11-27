function R=open_saved_gsl_nstep(show)
% Saved results only; never starts training.
if nargin<1,show=true;end
setupGSLNStep();here=fileparts(mfilename('fullpath'));S=readtable(fullfile(here,'summary.csv'));
policies=unique(S.policy,'stable');fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Max consecutive loss (packets)','On-time delivery (%)','Handovers'};
v='off';if show,v='on';end
f=figure('Visible',v,'Color','w','Name','GSL hysteresis and n-step DDQN - saved comparison','Position',[50 50 1350 830]);
layout=tiledlayout(f,2,2,'Padding','compact','TileSpacing','compact');
short={'SNR 0','SNR .1','SNR .3','SNR .5','DDQN 1','DDQN 3','DDQN 5'};
for j=1:4
    ax=nexttile(layout);mu=zeros(1,numel(policies));sd=mu;
    for k=1:numel(policies),row=S(strcmp(S.policy,policies(k))&strcmp(S.metric,fields{j}),:);mu(k)=row.mean;sd(k)=row.sampleSD;end
    b=bar(ax,mu,'FaceColor','flat');b.CData=[repmat([.3 .5 .75],4,1);.9 .5 .15;.35 .65 .35;.65 .4 .7];hold(ax,'on');
    errorbar(ax,1:numel(mu),mu,sd,'k.');grid(ax,'on');xticks(ax,1:numel(mu));xticklabels(ax,short);xtickangle(ax,20);
    ylabel(ax,labels{j});ylim(ax,[0 max(mu+sd)*1.25]);
    for k=1:numel(mu),text(ax,k,mu(k)+sd(k),sprintf('%.2f',mu(k)),'HorizontalAlignment','center','VerticalAlignment','bottom','FontSize',9);end
end
title(layout,{'6x11 | 6 dB | same 10 NEW seeds | mean +/- sample SD', ...
    'SNR: margin in dB | DDQN: maximum n-step horizon, 100 episodes each, original reward'});
exportgraphics(f,fullfile(here,'comparison.png'),'Resolution',160);savefig(f,fullfile(here,'comparison.fig'));
base=fullfile(here,'results_n1');out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));D=load(fullfile(out,'study.mat'),'R');R=D.R;R.outputDir=out;
disp(S);if ~show,close(f);end
end
