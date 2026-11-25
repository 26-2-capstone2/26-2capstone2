function T=compare_saved_gsl_ddqn_1000(show)
% Compare saved paired evaluations; no training or new simulation.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'ddqn_6x11')),gsl=fileparts(fileparts(mfilename('fullpath')));end
newRoot=fullfile(gsl,'ddqn_1000','results_ddqn_1000');
newOut=fullfile(newRoot,strtrim(fileread(fullfile(newRoot,'latest_result.txt'))));
oldRoot=fullfile(gsl,'ddqn_6x11','results_ddqn_6x11');
oldOut=fullfile(oldRoot,strtrim(fileread(fullfile(oldRoot,'latest_result.txt'))));
maxRoot=fullfile(gsl,'maxsnr_comparison','results_maxsnr','20261125_181004_310');
data={readtable(fullfile(maxRoot,'baseline_runs.csv')), ...
    readtable(fullfile(maxRoot,'maxsnr_runs.csv')), ...
    readtable(fullfile(oldOut,'runs.csv')),readtable(fullfile(newOut,'runs.csv'))};
names=["Elevation + 4 deg";"Max SNR";"DDQN 100";"DDQN 1000"];
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Max consecutive loss (packets)','On-time delivery (%)','Handovers'};
means=zeros(4,4);sds=means;
for k=1:4
    assert(height(data{k})==10 && isequal(data{k}.seed,data{4}.seed));
    for j=1:4,means(k,j)=mean(data{k}.(fields{j}));sds(k,j)=std(data{k}.(fields{j}));end
end
T=array2table(means,'VariableNames',fields);T=addvars(T,names,'Before',1,'NewVariableNames','policy');
writetable(T,fullfile(newOut,'four_policy_means.csv'));
paired=table();
for k=2:3
    for j=1:4
        d=data{4}.(fields{j})-data{k}.(fields{j});half=2.26215716274099*std(d)/sqrt(10);
        paired=[paired;table(names(k),string(fields{j}),mean(d),mean(d)-half,mean(d)+half, ...
            'VariableNames',{'reference','metric','DDQN1000_minus_reference','lower95','upper95'})]; %#ok<AGROW>
    end
end
writetable(paired,fullfile(newOut,'paired_differences_1000.csv'));
v='off';if show,v='on';end
f=figure('Name','Saved comparison - DDQN 100 vs 1000','Visible',v,'Color','w','Position',[50 50 1280 820]);
t=tiledlayout(f,2,2,'Padding','compact','TileSpacing','compact');
for j=1:4
    ax=nexttile(t);b=bar(ax,1:4,means(:,j),'FaceColor','flat');
    b.CData=[.55 .59 .65;.16 .61 .45;.25 .46 .75;.92 .44 .12];hold(ax,'on');
    errorbar(ax,1:4,means(:,j),sds(:,j),'k.','LineWidth',1);
    xticks(ax,1:4);xticklabels(ax,names);ylabel(ax,labels{j});grid(ax,'on');
    for k=1:4,text(ax,k,means(k,j)+sds(k,j),sprintf(' %.2f',means(k,j)), ...
            'HorizontalAlignment','center','VerticalAlignment','bottom','FontSize',10);end
    ylim(ax,[0 max(means(:,j)+sds(:,j))*1.20]);
end
title(t,{'6x11 | 6 dB | 10 paired test seeds | GS to first satellite', ...
    'Mean +/- sample SD; DDQN Q margin=0.02, Max SNR has no hysteresis'});
exportgraphics(f,fullfile(newOut,'four_policy_comparison.png'),'Resolution',160);
savefig(f,fullfile(newOut,'four_policy_comparison.fig'));
disp(T);disp(paired);
if ~show,close(f);end
end
