function f=plotGSLTrendResults(R,show)
if nargin<2,show=true;end
visibility='off';if show,visibility='on';end
f=figure('Visible',visibility,'Color','w','Name','DDQN 6x11 - Ten Evaluation Runs','Position',[60 60 1150 740]);
tiledlayout(f,2,2);fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss [%]','Max consecutive loss [packets]','On-time delivery [%]','Handovers'};
for j=1:4
    nexttile;bar(R.runs.repeat,R.runs.(fields{j}));hold on;
    yline(mean(R.runs.(fields{j})),'r--','Mean');grid on;xlabel('Held-out evaluation repeat');ylabel(labels{j});
end
sgtitle('DDQN ONLY | 6x11 | attenuation 6 dB | 600s | 100 training episodes + 10 held-out tests');
exportgraphics(f,fullfile(R.outputDir,'evaluation.png'),'Resolution',160);
g=figure('Visible',visibility,'Color','w','Name','DDQN 6x11 - Training','Position',[80 80 1100 650]);
tiledlayout(g,2,2);nexttile;plot(R.training.episode,R.training.reward);ylabel('Reward');
nexttile;plot(R.training.episode,R.training.loss_pct);ylabel('Exploratory loss [%]');
nexttile;plot(R.training.episode,R.training.epsilon);ylabel('Epsilon');
nexttile;plot(R.training.episode,R.training.trainingLoss);ylabel('Mean Huber training loss');
for ax=findall(g,'Type','axes').',grid(ax,'on');xlabel(ax,'Training episode');end
sgtitle('Training exploration: these are not held-out evaluation results');
exportgraphics(g,fullfile(R.outputDir,'training.png'),'Resolution',160);
if ~show,close(f);close(g);end
end
