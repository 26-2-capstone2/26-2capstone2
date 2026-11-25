function R=open_saved_gsl_ddqn_1000(show)
% Load saved results only. This function never starts training.
if nargin<1,show=true;end
here=fileparts(mfilename('fullpath'));
gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'ddqn_6x11'))
    gsl=fileparts(fileparts(mfilename('fullpath')));
end
addpath(gsl,fullfile(gsl,'three_constellations'),fullfile(gsl,'ddqn_6x11'),here);
resultRoot=fullfile(here,'results_ddqn_1000');
latest=fullfile(resultRoot,'latest_result.txt');
assert(isfile(latest),'Saved result is missing; no training was started.');
folder=strtrim(fileread(latest));out=fullfile(resultRoot,folder);
S=load(fullfile(out,'study.mat'),'R');R=S.R;R.outputDir=out;
assert(height(R.training)==1000 && height(R.runs)==10);
visibility='off';if show,visibility='on';end
f=figure('Visible',visibility,'Name','GSL DDQN - Saved 1000 Episode Training', ...
    'NumberTitle','off','Color','w','Position',[60 60 1200 780]);
t=tiledlayout(f,2,2);
fields={'loss_pct','maxLossRun','reward','handovers'};
labels={'Training packet loss (%)','Maximum loss run (packets)','Episode reward','Handovers'};
for j=1:4
    ax=nexttile(t);plot(ax,R.training.episode,R.training.(fields{j}),'LineWidth',1.2);
    grid(ax,'on');xlabel(ax,'Training episode');ylabel(ax,labels{j});xlim(ax,[1 1000]);
end
title(t,'SAVED | 1000 training episodes | 6x11 | 6 dB | exploratory training metrics');
savefig(f,fullfile(out,'training_monitor.fig'));
exportgraphics(f,fullfile(out,'training_monitor.png'),'Resolution',160);
g=figure('Visible',visibility,'Name','GSL DDQN - Saved Ten Evaluation Results', ...
    'NumberTitle','off','Color','w','Position',[100 80 1150 740]);
t=tiledlayout(g,2,2);
fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss (%)','Maximum loss run (packets)','On-time delivery (%)','Handovers'};
for j=1:4
    ax=nexttile(t);bar(ax,R.runs.repeat,R.runs.(fields{j}));hold(ax,'on');
    yline(ax,mean(R.runs.(fields{j})),'r--','Mean');grid(ax,'on');
    xlabel(ax,'Held-out evaluation repeat');ylabel(ax,labels{j});
end
title(t,'SAVED | 1000 training episodes + 10 held-out evaluations | epsilon=0');
savefig(g,fullfile(out,'evaluation.fig'));
exportgraphics(g,fullfile(out,'evaluation.png'),'Resolution',160);
disp(R.summary);
if show
    R.viewer=GSLTrendResultViewer(R);
    figure(f);
else
    close(f);close(g);
end
fprintf('Loaded saved results; NO retraining: %s\n',out);
end
