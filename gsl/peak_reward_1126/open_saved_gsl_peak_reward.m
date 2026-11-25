function R=open_saved_gsl_peak_reward(show)
% Reopen saved 14-input reward experiments; no new training.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'ddqn_6x11')),gsl=fileparts(fileparts(mfilename('fullpath')));end
addpath(gsl,fullfile(gsl,'three_constellations'),fullfile(gsl,'ddqn_6x11'),fullfile(gsl,'q_context_1126'),here);
modes={'control','peak'};data=cell(1,2);
for k=1:2
    base=fullfile(here,['results_' modes{k}]);out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
    S=load(fullfile(out,'study.mat'),'R');data{k}=S.R;data{k}.outputDir=out;
end
D=readtable(fullfile(here,'validation_new_seeds','runs.csv'));
v='off';if show,v='on';end
f=figure('Visible',v,'Color','w','Name','Aligned reward experiment - saved results','Position',[40 50 1400 820]);
t=tiledlayout(f,2,4,'Padding','compact','TileSpacing','compact');fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Max consecutive loss','On-time delivery (%)','Handovers'};
for cohort=1:2
    if cohort==1,A={data{1}.runs,data{2}.runs};else,A={D(strcmp(D.mode,'control'),:),D(strcmp(D.mode,'peak'),:)};end
    for j=1:4
        mu=zeros(1,2);sd=mu;for k=1:2,mu(k)=mean(A{k}.(fields{j}));sd(k)=std(A{k}.(fields{j}));end
        ax=nexttile(t);b=bar(ax,mu,'FaceColor','flat');b.CData=[.25 .46 .75;.92 .44 .12];hold(ax,'on');
        errorbar(ax,1:2,mu,sd,'k.');grid(ax,'on');xticks(ax,1:2);xticklabels(ax,{'Accum.','Peak'});
        ylabel(ax,labels{j});ylim(ax,[0 1.25*max(mu+sd)]);
        if cohort==1,title(ax,'Original 10 seeds');else,title(ax,'10 NEW seeds 20278001-10');end
        for k=1:2,text(ax,k,mu(k)+sd(k),sprintf(' %.3f',mu(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');end
    end
end
title(t,{'14-input controlled pilot | 6x11 | 6 dB | 100 episodes per arm', ...
    'Both: gamma=1, negative loss reward, no EXTRA HO cost | mean +/- SD'});
exportgraphics(f,fullfile(here,'aligned_reward_comparison.png'),'Resolution',160);savefig(f,fullfile(here,'aligned_reward_comparison.fig'));
R=data{2};disp(R.summary);
if show,R.viewer=GSLTrendResultViewer(R);figure(f);else,close(f);end
end
