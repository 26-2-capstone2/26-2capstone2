function R=open_saved_gsl_q_replay()
% Reopen saved replay-learning experiment without training.
here=fileparts(mfilename('fullpath'));root=fileparts(here);
if ~isfolder(fullfile(root,'ddqn_6x11')),root=fileparts(fileparts(mfilename('fullpath')));end
addpath(root,fullfile(root,'three_constellations'),fullfile(root,'ddqn_6x11'),here);
f=figure('Color','w','Name','Q learning replay comparison - saved results','Position',[60 60 1150 740]);
t=tiledlayout(f,2,2);fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Maximum consecutive loss','On-time delivery (%)','Handovers'};
modes={'uniform','prioritized'};data=cell(1,2);
for k=1:2
    base=fullfile(here,['results_' modes{k}]);out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
    S=load(fullfile(out,'study.mat'),'R');data{k}=S.R;data{k}.outputDir=out;
end
for j=1:4
    ax=nexttile(t);Y=[data{1}.runs.(fields{j}) data{2}.runs.(fields{j})];
    bar(ax,1:10,Y);grid(ax,'on');xlabel(ax,'Paired repeat');ylabel(ax,labels{j});
    legend(ax,{'Original uniform replay','TD-prioritized replay'},'Location','best');
end
title(t,'6x11 | 6 dB | 100 training episodes each | unchanged reward | 10 paired evaluations');
exportgraphics(f,fullfile(here,'q_replay_comparison.png'),'Resolution',160);savefig(f,fullfile(here,'q_replay_comparison.fig'));
R=data{2};R.viewer=GSLTrendResultViewer(R);
end
