function R=open_saved_gsl_q_context(show)
% Load only; this entry never starts training.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'ddqn_6x11')),gsl=fileparts(fileparts(mfilename('fullpath')));end
addpath(gsl,fullfile(gsl,'three_constellations'),fullfile(gsl,'ddqn_6x11'),here);
base=fullfile(here,'results_context');out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
S=load(fullfile(out,'study.mat'),'R');R=S.R;R.outputDir=out;
assert(height(R.training)==100&&height(R.runs)==10);
ref=readtable(fullfile(gsl,'ddqn_6x11','results_ddqn_6x11','20261123_160855_135','runs.csv'));
fresh=readtable(fullfile(here,'validation_new_seeds','runs.csv'));
v='off';if show,v='on';end
f=figure('Color','w','Visible',v,'Name','Candidate context input - saved comparison','Position',[60 60 1400 820]);
t=tiledlayout(f,2,4,'Padding','compact','TileSpacing','compact');
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Max consecutive loss','On-time delivery (%)','Handovers'};
for cohort=1:2
    if cohort==1,tables={ref,R.runs};else,tables={fresh(strcmp(fresh.mode,'uniform'),:),fresh(strcmp(fresh.mode,'context'),:)};end
    for j=1:4
        mu=zeros(1,2);sd=mu;
        for k=1:2,z=tables{k}.(fields{j});mu(k)=mean(z);sd(k)=std(z);end
        ax=nexttile(t);b=bar(ax,mu,'FaceColor','flat');b.CData=[.25 .46 .75;.92 .44 .12];hold(ax,'on');
        errorbar(ax,1:2,mu,sd,'k.');grid(ax,'on');xticks(ax,1:2);xticklabels(ax,{'Original','+ Context'});
        ylabel(ax,labels{j});ylim(ax,[0 1.25*max(mu+sd)]);
        if cohort==1,title(ax,'Original 10 test seeds');else,title(ax,'10 NEW seeds 20275001-10');end
        for k=1:2,text(ax,k,mu(k)+sd(k),sprintf(' %.3f',mu(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');end
    end
end
title(t,{'One added input: best visible estimated success | 100 training episodes each', ...
    '6x11 | 6 dB | original reward + uniform replay | mean +/- SD'});
exportgraphics(f,fullfile(here,'context_comparison.png'),'Resolution',160);savefig(f,fullfile(here,'context_comparison.fig'));
if show
    R.viewer=GSLTrendResultViewer(R);figure(f);
else,close(f);end
end
