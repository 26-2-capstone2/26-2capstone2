classdef GSLTrendResultViewer < handle
    properties (SetAccess=private)
        Figure;PacketViewer;CurrentTime_s=0
    end
    properties (Access=private)
        R;Choice;Header;TimeSlider;CandidateTable;Preview;Geometry;
        Timer;LastIndex=-1;SnrAxis;RunAxis;Cursor;Busy=false
    end
    methods
        function obj=GSLTrendResultViewer(R)
            obj.R=R;S=load(fullfile(R.outputDir,'geometry.mat'),'geometry');obj.Geometry=S.geometry;
            screen=get(groot,'ScreenSize');
            obj.Figure=figure('Name','DDQN 6x11 / 6 dB - Ten Evaluation Runs','Color','w', ...
                'Position',[25 40 min(1200,screen(3)-60) min(850,screen(4)-130)]);
            f=obj.Figure;setappdata(f,'Controller',obj);f.CloseRequestFcn=@(~,~)delete(obj);
            obj.Header=uicontrol(f,'Style','text','Units','normalized','Position',[.02 .92 .96 .065], ...
                'BackgroundColor','w','HorizontalAlignment','left','FontSize',11);
            names=arrayfun(@(k)sprintf('Evaluation %02d | seed %d',k,R.runs.seed(k)),1:height(R.runs),'UniformOutput',false);
            obj.Choice=uicontrol(f,'Style','popupmenu','Units','normalized','Position',[.02 .865 .45 .045], ...
                'String',names,'Callback',@(~,~)obj.loadRepeat());
            uicontrol(f,'Style','text','Units','normalized','Position',[.49 .865 .49 .04], ...
                'String','Play / Pause / Speed: numbered packet window','BackgroundColor','w');
            cols={'repeat','loss_pct','onTime_pct','maxLossRun','handovers'};
            uitable(f,'Units','normalized','Position',[.02 .62 .96 .23], ...
                'Data',table2array(R.runs(:,cols)),'ColumnName',{'repeat','loss %','on-time %','max loss run','handovers'}, ...
                'ColumnWidth',{85 140 140 150 130},'RowName',[]);
            obj.SnrAxis=axes(f,'Position',[.065 .36 .48 .20]);
            obj.RunAxis=axes(f,'Position',[.065 .10 .48 .18]);
            obj.CandidateTable=uitable(f,'Units','normalized','Position',[.59 .10 .39 .48], ...
                'ColumnName',{'ID','SNR dB','1s delta','5s trend','elevation','PER','serving'},'RowName',[]);
            obj.TimeSlider=uicontrol(f,'Style','slider','Units','normalized','Position',[.05 .025 .90 .03], ...
                'Min',0,'Max',600,'Callback',@(src,~)obj.seek(src.Value));
            obj.loadRepeat();
            obj.Timer=timer('ExecutionMode','fixedSpacing','Period',.2,'BusyMode','drop','TimerFcn',@(~,~)obj.refresh());
            start(obj.Timer);
        end
        function seek(obj,t)
            obj.CurrentTime_s=max(0,min(600,t));obj.PacketViewer.setTime(obj.CurrentTime_s);
            obj.LastIndex=-1;obj.refresh();
        end
        function loadRepeat(obj)
            obj.Busy=true;guard=onCleanup(@()obj.unlock()); %#ok<NASGU>
            k=obj.Choice.Value;S=load(fullfile(obj.R.outputDir,sprintf('repeat_%02d',k),'preview.mat'),'preview');
            obj.Preview=S.preview;C=configGSLToolboxPHY(obj.Preview.config);
            C.experimentLabel=sprintf('DDQN 6x11 | 6 dB | evaluation %02d | seed %d',k,obj.Preview.seed);
            Q=struct('packetTable',obj.Preview.P,'linkState',obj.Preview.L,'config',C);
            if isempty(obj.PacketViewer)||~isvalid(obj.PacketViewer)||~isgraphics(obj.PacketViewer.Figure)
                obj.PacketViewer=GSLPacketViewer(Q.packetTable,Q.linkState,C,[],C.startTime);
            else,obj.PacketViewer.setWeatherCase(Q);end
            obj.PacketViewer.setTime(obj.CurrentTime_s);
            quality=obj.Preview.snr;quality(~obj.Geometry.isVisible)=NaN;
            cla(obj.SnrAxis);plot(obj.SnrAxis,obj.Geometry.time_s,max(quality,[],2,'omitnan'),'g');hold(obj.SnrAxis,'on');
            plot(obj.SnrAxis,obj.Preview.L.time_s,obj.Preview.L.snr_dB,'b');
            obj.Cursor=xline(obj.SnrAxis,obj.CurrentTime_s,'r--');grid(obj.SnrAxis,'on');
            xlim(obj.SnrAxis,[0 600]);ylabel(obj.SnrAxis,'SNR [dB]');legend(obj.SnrAxis,{'Best visible','DDQN selected'},'Location','best');
            runs=obj.Preview.M.lossRuns;cla(obj.RunAxis);
            stem(obj.RunAxis,runs.firstGeneration_s,runs.length_packets,'.');grid(obj.RunAxis,'on');
            xlim(obj.RunAxis,[0 600]);xlabel(obj.RunAxis,'Generation time [s]');ylabel(obj.RunAxis,'Consecutive lost packets');
            obj.LastIndex=-1;obj.Busy=false;obj.refresh();
        end
        function refresh(obj)
            if obj.Busy||~isgraphics(obj.Figure),return;end
            obj.CurrentTime_s=min(600,obj.PacketViewer.CurrentTime_s);obj.TimeSlider.Value=obj.CurrentTime_s;
            obj.Cursor.Value=obj.CurrentTime_s;index=min(600,floor(obj.CurrentTime_s)+1);
            if index==obj.LastIndex,return;end
            obj.LastIndex=index;G=obj.Geometry;ids=find(G.isVisible(index,:)).';q=obj.Preview.snr(index,ids).';
            [q,order]=sort(q,'descend');ids=ids(order);delta=zeros(size(ids));trend=delta;
            for j=1:numel(ids)
                h=0;while h<min(5,index-1)&&G.isVisible(index-1-h,ids(j)),h=h+1;end
                if h>0
                    trend(j)=(q(j)-obj.Preview.snr(index-h,ids(j)))/h;
                    delta(j)=q(j)-obj.Preview.snr(index-1,ids(j));
                end
            end
            C=configGSLToolboxPHY(obj.Preview.config);per=getPERfromSNR(q,C);
            obj.CandidateTable.Data=[ids,q,delta,trend,G.elevation_deg(index,ids).',per,double(ids==obj.Preview.L.servingSatID(index))];
            M=obj.Preview.M;
            obj.Header.String=sprintf(['GS -> FIRST SATELLITE ONLY | 6x11 | 6 dB | DDQN evaluation %02d | replay %.1f s (snapshot %d s)\n' ...
                '600s result: loss %.4f%% | on-time %.4f%% | max loss run %d | HO %d | %d visible candidates'], ...
                obj.Choice.Value,obj.CurrentTime_s,index-1,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
                M.maxConsecutiveLoss,sum(obj.Preview.L.handoverEvent),numel(ids));
        end
        function unlock(obj),obj.Busy=false;end
        function delete(obj)
            if ~isempty(obj.Timer)&&isvalid(obj.Timer),stop(obj.Timer);delete(obj.Timer);end
            if ~isempty(obj.PacketViewer)&&isvalid(obj.PacketViewer),delete(obj.PacketViewer);end
            if isgraphics(obj.Figure),obj.Figure.CloseRequestFcn='';delete(obj.Figure);end
        end
    end
end
