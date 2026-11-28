function R=open_saved_gsl_stay_switch(show)
% Saved results only; neither forks nor training run in this entry point.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'ddqn_6x11')),gsl=fileparts(fileparts(mfilename('fullpath')));end
addpath(gsl,fullfile(gsl,'three_constellations'),fullfile(gsl,'ddqn_6x11'),fullfile(gsl,'q_context_1126'),here);
base=fullfile(here,'results_paired');out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
S=load(fullfile(out,'study.mat'),'R');R=S.R;R.outputDir=out;
ref=readtable(fullfile(gsl,'q_context_1126','results_context','20261126_003447_332','runs.csv'));
fresh=readtable(fullfile(here,'validation_new_seeds','runs.csv'));
v='off';if show,v='on';end
f=figure('Name','Paired stay/switch learning - saved results','Visible',v,'Color','w','Position',[50 50 1400 820]);
t=tiledlayout(f,2,4,'Padding','compact','TileSpacing','compact');
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};labels={'Packet loss (%)','Max consecutive loss','On-time delivery (%)','Handovers'};
for cohort=1:2
    if cohort==1,tables={ref,R.runs};else,tables={fresh(strcmp(fresh.mode,'context'),:),fresh(strcmp(fresh.mode,'paired'),:)};end
    for j=1:4
        mu=zeros(1,2);sd=mu;
        for k=1:2,z=tables{k}.(fields{j});mu(k)=mean(z);sd(k)=std(z);end
        ax=nexttile(t);b=bar(ax,mu,'FaceColor','flat');b.CData=[.25 .46 .75;.92 .44 .12];hold(ax,'on');
        errorbar(ax,1:2,mu,sd,'k.');grid(ax,'on');xticks(ax,1:2);xticklabels(ax,{'Parent','Paired'});
        ylabel(ax,labels{j});ylim(ax,[0 1.25*max(mu+sd)]);
        if cohort==1,title(ax,'Original 10 seeds');else,title(ax,'10 NEW seeds 20276001-10');end
        for k=1:2,text(ax,k,mu(k)+sd(k),sprintf(' %.3f',mu(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');end
    end
end
title(t,{'Stay/switch paired experience | 100 primary episodes each | 6x11 | 6 dB', ...
    'Same 12 inputs and reward | 8 rare + 56 normal samples | mean +/- SD'});
exportgraphics(f,fullfile(here,'paired_learning_comparison.png'),'Resolution',160);savefig(f,fullfile(here,'paired_learning_comparison.fig'));
P=readtable(fullfile(here,'stay_switch_diagnostics','pairs.csv'));
g=figure('Name','Stay or switch - frozen parent diagnostic','Visible',v,'Color','w','Position',[70 80 1150 420]);
tt=tiledlayout(g,1,2);ax=nexttile(tt);
bar(ax,[sum(P.switchMinusStayReturn< -1e-9),sum(P.switchMinusStayReturn>1e-9)]);xticks(ax,1:2);xticklabels(ax,{'Stay better','Switch better'});ylabel(ax,'Decision cases');grid(ax,'on');title(ax,'Higher discounted reward');
ax=nexttile(tt);bar(ax,[sum(P.stayWindowLoss<P.switchWindowLoss),sum(P.switchWindowLoss<P.stayWindowLoss),sum(P.switchWindowLoss==P.stayWindowLoss)]);
xticks(ax,1:3);xticklabels(ax,{'Stay fewer','Switch fewer','Tie'});ylabel(ax,'Decision cases');grid(ax,'on');title(ax,'Fewer lost packets in the window');
title(tt,{'First 1-second action only, then same frozen parent policy | horizon up to 60s', ...
    '92 eligible TRAINING cases; correlated decision times, not independent trials'});
exportgraphics(g,fullfile(here,'stay_switch_diagnostic.png'),'Resolution',160);savefig(g,fullfile(here,'stay_switch_diagnostic.fig'));
if show,R.viewer=GSLTrendResultViewer(R);figure(f);else,close(f);close(g);end
end
