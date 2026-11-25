function show_training_monitor()
% Read-only live view of the separate training process.
root=fileparts(mfilename('fullpath'));
f=figure('Name','GSL DDQN - 1000 Episode Training Monitor','NumberTitle','off', ...
    'Position',[80 80 1200 780],'Color','w');
t=tiledlayout(f,2,2,'Padding','compact');
names={'loss_pct','maxLossRun','reward','handovers'};
labels={'Training packet loss (%)','Maximum loss run (packets)','Episode reward','Handovers'};
lines=gobjects(1,4);
for j=1:4
    ax=nexttile(t);lines(j)=plot(ax,NaN,NaN,'LineWidth',1.2);
    grid(ax,'on');xlabel(ax,'Training episode');ylabel(ax,labels{j});xlim(ax,[1 1000]);
end
title(t,'Waiting for training log...');
tm=timer('ExecutionMode','fixedSpacing','Period',5,'BusyMode','drop','TimerFcn',@refresh);
f.CloseRequestFcn=@cleanup;
refresh();start(tm);
fprintf('Live monitor only: training continues in a separate MATLAB process.\n');
fprintf('Closing this figure does not stop training.\n');
    function refresh(varargin)
        if ~isgraphics(f),return;end
        dirs=dir(fullfile(root,'results_ddqn_1000','20*'));
        dirs=dirs([dirs.isdir]);if isempty(dirs),return;end
        [~,ix]=max([dirs.datenum]);out=fullfile(dirs(ix).folder,dirs(ix).name);
        try
            A=readtable(fullfile(out,'training.csv'));
            if isempty(A),return;end
            for k=1:4,set(lines(k),'XData',A.episode,'YData',A.(names{k}));end
            stage='TRAINING';
            if isfile(fullfile(out,'runs.csv'))
                B=readtable(fullfile(out,'runs.csv'));
                stage=sprintf('EVALUATING %d/10',height(B));
            end
            if isfile(fullfile(out,'study.mat')),stage='COMPLETE';end
            title(t,sprintf('%s | %d / 1000 episodes | 6x11 | 6 dB | refreshed %s', ...
                stage,A.episode(end),char(datetime('now','Format','HH:mm:ss'))));
            drawnow limitrate;
        catch
            % Writer may briefly be replacing the CSV; retry on next timer tick.
        end
    end
    function cleanup(varargin)
        stop(tm);delete(tm);delete(f);
    end
end
