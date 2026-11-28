function open_saved_gsl_reward_audit(show)
% Display stored audit only. No training, policy change, or new simulation.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));P=readtable(fullfile(here,'full_episode_audit','full_episode_pairs.csv'));
E=P(P.seed==20269137&P.time_s==599,:);assert(height(E)==1);
v='off';if show,v='on';end
f=figure('Visible',v,'Color','w','Name','Reward alignment - actual GSL case','Position',[60 60 1200 800]);
t=tiledlayout(f,2,2);data={[E.stayFullLoss E.switchFullLoss],[E.stayFullMaxRun E.switchFullMaxRun],[E.stayReturn E.switchReturn]};
labels={'Total lost packets in 600s','Maximum consecutive loss in 600s','Final-second reward (higher is better)'};
for j=1:3
    ax=nexttile(t);z=data{j};b=bar(ax,z,'FaceColor','flat');b.CData=[.25 .46 .75;.92 .44 .12];
    xticks(ax,1:2);xticklabels(ax,{'Stay','Switch'});ylabel(ax,labels{j});grid(ax,'on');
    if j<3,ylim(ax,[0 max(z)*1.2]);else,ylim(ax,[min(z)*1.2 0]);end
    for k=1:2
        va='bottom';if j==3,va='top';end
        text(ax,k,z(k),sprintf(' %.4f',z(k)),'HorizontalAlignment','center','VerticalAlignment',va);
    end
end
ax=nexttile(t);z=[E.successContribution E.burstContribution E.HOContribution E.switchMinusStayReturn];
bar(ax,z);xticks(ax,1:4);xticklabels(ax,{'Receive','Burst','Extra HO','Net'});yline(ax,0,'k-');grid(ax,'on');
ylabel(ax,'Switch minus stay reward');ylim(ax,[-.13 .12]);
for k=1:4,va='bottom';if z(k)<0,va='top';end;text(ax,k,z(k),sprintf(' %.5f',z(k)),'HorizontalAlignment','center','VerticalAlignment',va);end
title(t,{'Actual simulator example | seed 20269137 | choice at t=599 s', ...
    'Switch loses 1 fewer packet and has a shorter maximum, but extra HO cost reverses reward ranking'});
exportgraphics(f,fullfile(here,'reward_alignment_actual.png'),'Resolution',160);savefig(f,fullfile(here,'reward_alignment_actual.fig'));
S=readtable(fullfile(here,'rescoring_summary.csv'));
names={'original','no_extra_HO','no_discount','no_burst'};counts=zeros(1,4);
for k=1:4,counts(k)=S.preferLongerFullMax(strcmp(S.scoring,names{k}));end
g=figure('Visible',v,'Color','w','Name','Fixed trajectory reward rescoring','Position',[80 80 1100 500]);
bar(counts);xticks(1:4);xticklabels({'Original','No extra HO term','No discount','No burst term'});grid on;
ylabel('Higher reward prefers longer full-episode maximum');ylim([0 max(counts)*1.2]);
for k=1:4,text(k,counts(k),sprintf(' %d / 92',counts(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');end
title({'Fixed-trajectory diagnostic scores ONLY','No retraining or changed-policy performance evaluation; cases are correlated'});
exportgraphics(g,fullfile(here,'fixed_trajectory_rescoring.png'),'Resolution',160);savefig(g,fullfile(here,'fixed_trajectory_rescoring.fig'));
disp(E);disp(S);
if ~show,close(f);close(g);end
end
