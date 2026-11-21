classdef GSLThreeResultViewer < handle
    properties (SetAccess=private)
        Figure; PacketViewer; CurrentTime_s=0
    end
    properties (Access=private)
        R; GridChoice; PolicyChoice; Header; TimeSlider; CandidateTable;
        Preview; Geometry; Timer; LastIndex=-1; SnrAxis; RunAxis; Cursor; Busy=false;
    end
    methods
        function obj=GSLThreeResultViewer(R)
            obj.R=R; screen=get(groot,'ScreenSize');
            f=figure('Name','GSL - Three Constellations / Candidates','Color','w', ...
                'Position',[25 40 min(1200,screen(3)-60) min(850,screen(4)-130)]);
            obj.Figure=f;setappdata(f,'Controller',obj); f.CloseRequestFcn=@(~,~)delete(obj);
            obj.Header=uicontrol(f,'Style','text','Units','normalized','Position',[.02 .93 .96 .055], ...
                'BackgroundColor','w','HorizontalAlignment','left','FontSize',11);
            obj.GridChoice=uicontrol(f,'Style','popupmenu','Units','normalized','Position',[.02 .875 .18 .04], ...
                'String',{'6 x 11 (66)','20 x 20 (400)','36 x 36 (1296)'},'Callback',@(~,~)obj.loadCase());
            obj.PolicyChoice=uicontrol(f,'Style','popupmenu','Units','normalized','Position',[.22 .875 .31 .04], ...
                'String',{'Max-SNR','Max-SNR + 0.1 dB','Candidate DDQN + Q margin'},'Value',3, ...
                'Callback',@(~,~)obj.loadCase());
            uicontrol(f,'Style','text','Units','normalized','Position',[.55 .875 .43 .035], ...
                'BackgroundColor','w','String','Play / Pause / Speed: use the numbered packet window.');
            data=table2cell(R.summary);
            for k=1:numel(data),if isstring(data{k}),data{k}=char(data{k});end,end
            uitable(f,'Units','normalized','Position',[.02 .64 .96 .22], ...
                'Data',data,'ColumnName',R.summary.Properties.VariableNames,'RowName',[]);
            obj.SnrAxis=axes(f,'Position',[.065 .37 .48 .20]);
            obj.RunAxis=axes(f,'Position',[.065 .10 .48 .19]);
            obj.CandidateTable=uitable(f,'Units','normalized','Position',[.59 .10 .39 .49], ...
                'ColumnName',{'rank','satellite ID','p','s','SNR dB','elevation','PER','serving'},'RowName',[]);
            obj.TimeSlider=uicontrol(f,'Style','slider','Units','normalized','Position',[.05 .025 .90 .03], ...
                'Min',0,'Max',600,'Value',0,'Callback',@(src,~)obj.seek(src.Value));
            obj.loadCase();
            obj.Timer=timer('ExecutionMode','fixedSpacing','Period',.2,'BusyMode','drop', ...
                'TimerFcn',@(~,~)obj.refresh());start(obj.Timer);
        end
        function seek(obj,t)
            obj.CurrentTime_s=max(0,min(600,t));obj.PacketViewer.setTime(obj.CurrentTime_s);
            obj.LastIndex=-1;obj.refresh();
        end
        function loadCase(obj)
            obj.Busy=true;guard=onCleanup(@()obj.unlock()); %#ok<NASGU>
            k=obj.GridChoice.Value; names=["MaxSNR","MaxSNR_Hysteresis","DDQN"];
            policy=names(obj.PolicyChoice.Value); sizes=obj.R.options.sizes(k,:);
            folder=fullfile(obj.R.outputDir,sprintf('grid_%dx%d',sizes(1),sizes(2)),char(policy));
            S=load(fullfile(folder,'preview.mat'),'preview'); obj.Preview=S.preview;
            S=load(fullfile(obj.R.outputDir,sprintf('geometry_%dx%d.mat',sizes(1),sizes(2))),'geometry');
            obj.Geometry=S.geometry;
            Q=struct('packetTable',obj.Preview.P,'linkState',obj.Preview.L, ...
                'config',configGSLToolboxPHY(obj.Preview.config));
            Q.config.experimentLabel=sprintf('%dx%d | %s | seed %d | 8 dB',sizes(1),sizes(2),policy,obj.Preview.seed);
            if isempty(obj.PacketViewer) || ~isvalid(obj.PacketViewer) || ~isgraphics(obj.PacketViewer.Figure)
                obj.PacketViewer=GSLPacketViewer(Q.packetTable,Q.linkState,Q.config,[],Q.config.startTime);
            else,obj.PacketViewer.setWeatherCase(Q);end
            obj.PacketViewer.setTime(obj.CurrentTime_s);
            G=obj.Geometry; quality=obj.Preview.snr;quality(~G.isVisible)=NaN;
            best=max(quality,[],2,'omitnan');
            cla(obj.SnrAxis);plot(obj.SnrAxis,G.time_s,best,'g','LineWidth',1.2);hold(obj.SnrAxis,'on');
            plot(obj.SnrAxis,obj.Preview.L.time_s,obj.Preview.L.snr_dB,'b');
            obj.Cursor=xline(obj.SnrAxis,obj.CurrentTime_s,'r--');grid(obj.SnrAxis,'on');
            ylabel(obj.SnrAxis,'SNR [dB]');xlim(obj.SnrAxis,[0 600]);legend(obj.SnrAxis,{'Best visible','Selected'},'Location','best');
            cla(obj.RunAxis);runs=obj.Preview.M.lossRuns;
            stem(obj.RunAxis,runs.firstGeneration_s,runs.length_packets,'.');grid(obj.RunAxis,'on');
            xlim(obj.RunAxis,[0 600]);xlabel(obj.RunAxis,'Time [s]');ylabel(obj.RunAxis,'Consecutive lost packets');
            obj.LastIndex=-1;obj.Busy=false;obj.refresh();
        end
        function refresh(obj)
            if obj.Busy || ~isgraphics(obj.Figure),return;end
            if ~isempty(obj.PacketViewer) && isvalid(obj.PacketViewer)
                obj.CurrentTime_s=min(600,obj.PacketViewer.CurrentTime_s);
            end
            obj.TimeSlider.Value=obj.CurrentTime_s;
            if ~isempty(obj.Cursor)&&isgraphics(obj.Cursor),obj.Cursor.Value=obj.CurrentTime_s;end
            index=min(600,floor(obj.CurrentTime_s)+1);
            if index==obj.LastIndex,return;end
            obj.LastIndex=index;G=obj.Geometry; C=obj.Preview.config; t=G.time_s(index);
            ids=find(G.isVisible(index,:)).';quality=obj.Preview.snr(index,ids).';
            [quality,order]=sort(quality,'descend');ids=ids(order);
            per=getPERfromSNR(quality,configGSLToolboxPHY(C));
            serving=obj.Preview.L.servingSatID(index);
            obj.CandidateTable.Data=[(1:numel(ids)).',ids,G.planeIndex(ids)+1,G.satelliteInPlane(ids)+1, ...
                quality,G.elevation_deg(index,ids).',per,double(ids==serving)];
            M=obj.Preview.M;
            obj.Header.String=sprintf(['GS -> FIRST SATELLITE ONLY | %dx%d | %s | replay %.1f s (candidate snapshot %.0f s)\n' ...
                '600s result: PLR %.3f%% | on-time %.3f%% | max run %d | HO %d | candidates %d | elevation >=25 deg, no radius/top-K limit'], ...
                C.numPlanes,C.satsPerPlane,obj.Preview.policy,obj.CurrentTime_s,t, ...
                M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(obj.Preview.L.handoverEvent),numel(ids));
        end
        function delete(obj)
            if ~isempty(obj.Timer)&&isvalid(obj.Timer),stop(obj.Timer);delete(obj.Timer);end
            if ~isempty(obj.PacketViewer)&&isvalid(obj.PacketViewer),delete(obj.PacketViewer);end
            if isgraphics(obj.Figure),obj.Figure.CloseRequestFcn='';delete(obj.Figure);end
        end
        function unlock(obj),obj.Busy=false;end
    end
end
