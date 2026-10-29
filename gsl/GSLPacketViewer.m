classdef GSLPacketViewer < handle
    % Packet records are precomputed; their outcomes are revealed by playback time.
    properties (SetAccess=private)
        Figure
        CurrentTime_s = 0
        WeatherName = ""
    end
    properties (Access=private)
        P; L; C; NativeViewer; StartTime
        Clock; Header; LinkLabel; Detail; Boxes; Labels; Follow; Jump
        Slider; Speed; Playing = false; LastTick; LastRender = -Inf
        SelectedID = 0; WindowEnd = 0
    end
    methods
        function obj=GSLPacketViewer(P,L,C,viewer,startTime)
            obj.P=P; obj.L=L; obj.C=C; obj.NativeViewer=viewer; obj.StartTime=startTime;
            obj.WeatherName=string(C.channelScenario);
            old=findall(groot,'Type','figure','Tag','GSLPacketViewer');
            if ~isempty(old), close(old); end
            f=figure('Name','GSL Uplink - Packet IDs and Outcomes','NumberTitle','off', ...
                'Color','w','Tag','GSLPacketViewer','Position',[100 70 1250 800]);
            obj.Figure=f; setappdata(f,'Controller',obj);
            f.CloseRequestFcn=@(~,~)delete(obj);
            obj.Header=uicontrol(f,'Style','text','Units','normalized','Position',[.02 .90 .96 .08], ...
                'BackgroundColor','w','HorizontalAlignment','left','FontSize',12);
            obj.LinkLabel=uicontrol(f,'Style','text','Units','normalized','Position',[.02 .85 .96 .05], ...
                'BackgroundColor','w','HorizontalAlignment','left','FontSize',10);
            uicontrol(f,'Style','text','Units','normalized','Position',[.02 .81 .96 .04], ...
                'BackgroundColor','w','HorizontalAlignment','left', ...
                'String','Black = on time | White = lost | Orange = late arrival | Gray = pending | Click a numbered box for its record');
            ax=axes(f,'Position',[.025 .27 .95 .53]); axis(ax,'off');
            cols=20; count=C.packetDisplayCount; rows=ceil(count/cols);
            xlim(ax,[0 cols]); ylim(ax,[0 rows]); ax.YDir='reverse'; hold(ax,'on');
            obj.Boxes=gobjects(count,1); obj.Labels=gobjects(count,1);
            for k=1:count
                x=mod(k-1,cols); y=floor((k-1)/cols);
                obj.Boxes(k)=rectangle(ax,'Position',[x+.04 y+.06 .92 .85], ...
                    'FaceColor',[.85 .85 .85],'EdgeColor',[.35 .35 .35], ...
                    'ButtonDownFcn',@(src,~)obj.selectPacket(src.UserData));
                obj.Labels(k)=text(ax,x+.5,y+.5,'','FontSize',7,'HorizontalAlignment','center', ...
                    'HitTest','off','PickableParts','none');
            end
            obj.Follow=uicontrol(f,'Style','checkbox','Units','normalized','Position',[.02 .22 .20 .035], ...
                'String','Follow current packets','Value',1,'BackgroundColor','w', ...
                'Callback',@(~,~)obj.render(true));
            obj.Jump=uicontrol(f,'Style','edit','Units','normalized','Position',[.24 .22 .10 .035], ...
                'String','1','Callback',@(~,~)obj.jumpToPacket());
            uicontrol(f,'Style','pushbutton','Units','normalized','Position',[.35 .22 .13 .035], ...
                'String','Inspect packet ID','Callback',@(~,~)obj.jumpToPacket());
            obj.Detail=uicontrol(f,'Style','text','Units','normalized','Position',[.02 .06 .96 .15], ...
                'BackgroundColor',[.95 .97 1],'HorizontalAlignment','left','FontSize',11, ...
                'String','Select a packet. Scope: ground station -> first satellite only.');
            if isempty(viewer)
                obj.Slider=uicontrol(f,'Style','slider','Units','normalized','Position',[.02 .015 .70 .03], ...
                    'Min',0,'Max',max(C.duration_s,max(P.finalTime_s(isfinite(P.finalTime_s)))), ...
                    'Callback',@(s,~)obj.setTime(s.Value));
                uicontrol(f,'Style','pushbutton','Units','normalized','Position',[.74 .01 .10 .04], ...
                    'String','Play / Pause','Callback',@(~,~)obj.toggle());
                obj.Speed=uicontrol(f,'Style','popupmenu','Units','normalized','Position',[.86 .01 .10 .04], ...
                    'String',{'1x','5x','20x','60x'},'Value',1);
            else
                uicontrol(f,'Style','text','Units','normalized','Position',[.02 .01 .96 .04], ...
                    'BackgroundColor','w','String','Time follows the 3D viewer: use its native Play / Pause / Speed / Seek controls.');
            end
            obj.render(true); obj.LastTick=tic;
            % A native viewer has exactly one clock reader (its controller).
            % A second timer reading CurrentTime can re-enter the Globe bridge
            % while a seek is waiting for its acknowledgement.
            if isempty(viewer)
                obj.Clock=timer('ExecutionMode','fixedSpacing','Period',.1,'BusyMode','drop', ...
                    'TimerFcn',@(~,~)obj.tick());
                start(obj.Clock);
            end
        end
        function setTime(obj,t)
            obj.CurrentTime_s=max(0,t); obj.render(false);
        end
        function setWeatherCase(obj,Q)
            % Reuse the same grid and playback time; never recreate the native viewer.
            assert(height(Q.packetTable)==height(obj.P));
            obj.P=Q.packetTable; obj.L=Q.linkState; obj.C=Q.config;
            obj.WeatherName=string(Q.config.channelScenario);
            obj.render(true);
        end
        function delete(obj)
            if ~isempty(obj.Clock) && isvalid(obj.Clock), stop(obj.Clock); delete(obj.Clock); end
            if isgraphics(obj.Figure), obj.Figure.CloseRequestFcn=''; delete(obj.Figure); end
        end
    end
    methods (Access=private)
        function toggle(obj), obj.Playing=~obj.Playing; obj.LastTick=tic; end
        function tick(obj)
            if ~isgraphics(obj.Figure), delete(obj); return; end
            dt=toc(obj.LastTick); obj.LastTick=tic;
            if ~isempty(obj.NativeViewer)
                if ~isvalid(obj.NativeViewer), delete(obj); return; end
                obj.CurrentTime_s=seconds(obj.NativeViewer.CurrentTime-obj.StartTime);
            elseif obj.Playing
                speeds=[1 5 20 60];
                obj.CurrentTime_s=min(obj.Slider.Max,obj.CurrentTime_s+dt*speeds(obj.Speed.Value));
                obj.Slider.Value=obj.CurrentTime_s;
                if obj.CurrentTime_s>=obj.Slider.Max, obj.Playing=false; end
            end
            obj.render(false);
        end
        function jumpToPacket(obj)
            id=str2double(obj.Jump.String);
            if ~isscalar(id) || ~isfinite(id) || id<1 || id>height(obj.P) || fix(id)~=id, return; end
            obj.Follow.Value=0; obj.WindowEnd=min(height(obj.P),max(obj.C.packetDisplayCount,id));
            obj.SelectedID=id; obj.render(true);
        end
        function selectPacket(obj,id)
            if isempty(id) || id<1, return; end
            obj.SelectedID=id; obj.Jump.String=num2str(id); obj.render(true);
        end
        function render(obj,force)
            t=obj.CurrentTime_s;
            if ~force && abs(t-obj.LastRender)<.08, return; end
            obj.LastRender=t; P=obj.P; generated=P.time_s<=t;
            done=generated & P.finalTime_s<=t & ~P.outcome_pending;
            lost=done & P.lost==1; late=done & P.late; ontime=done & P.onTime;
            pending=generated & ~done; n=sum(generated); denom=max(1,n);
            e=diff([false;lost;false]); lengths=find(e==-1)-find(e==1);
            longest=0; if ~isempty(lengths), longest=max(lengths); end
            if any(pending), phase='provisional; pending included in denominator'; else, phase='resolved generated packets'; end
            obj.Header.String=sprintf(['GSL UPLINK | %s | %.3f s | Deadline %.1f ms\n' ...
                'Generated %d | On-time %d | Late %d | Lost %d | Pending %d | Max loss run %d\n' ...
                'Loss %.3f%% | On-time %.3f%% | Deadline failure %.3f%% (%s)'], ...
                obj.C.channelScenario,t,1000*obj.C.gslDeadline_s,n,sum(ontime),sum(late),sum(lost),sum(pending),longest, ...
                100*sum(lost)/denom,100*sum(ontime)/denom,100*sum(lost|late)/denom,phase);
            k=find(obj.L.time_s<=t,1,'last'); if isempty(k), k=1; end
            p=find(generated,1,'last'); snr=obj.L.snr_dB(k);
            if ~isempty(p), snr=P.snr_dB(p); end
            ht=obj.L.time_s(obj.L.handoverEvent);
            state='CONNECTED';
            if any(t>=ht & t<ht+obj.C.handoverInterruption_s), state='HANDOVER: not transmitting'; end
            if obj.L.servingSatID(k)==0, state='NO VISIBLE SATELLITE'; end
            obj.LinkLabel.String=sprintf('GS -> satellite %d | %s | SNR %.2f dB | Tx %.2f dBW | Experimental channel', ...
                obj.L.servingSatID(k),state,snr,obj.C.groundTxPower_dBW);
            count=numel(obj.Boxes);
            if obj.Follow.Value, last=max(count,n); else, last=obj.WindowEnd; end
            first=max(1,last-count+1);
            for k=1:count
                id=first+k-1;
                if id>height(P), obj.Boxes(k).Visible='off'; obj.Labels(k).String=''; continue; end
                obj.Boxes(k).Visible='on'; obj.Boxes(k).UserData=id;
                color=[.85 .85 .85]; ink=[.3 .3 .3];
                if generated(id) && done(id)
                    if lost(id), color=[1 1 1]; ink=[0 0 0];
                    elseif late(id), color=[1 .65 .15]; ink=[0 0 0];
                    else, color=[0 0 0]; ink=[1 1 1]; end
                end
                obj.Boxes(k).FaceColor=color; obj.Labels(k).Color=ink;
                obj.Labels(k).String=num2str(id);
                if obj.SelectedID==id, obj.Boxes(k).LineWidth=2.5; else, obj.Boxes(k).LineWidth=.5; end
            end
            id=obj.SelectedID;
            if id>0
                if ~generated(id)
                    obj.Detail.String=sprintf('Packet %d: not generated yet (generation %.6f s).',id,P.time_s(id));
                elseif ~done(id)
                    obj.Detail.String=sprintf('Packet %d: PENDING | GS -> satellite %d | generated %.6f s\nNo future outcome is revealed.', ...
                        id,P.servingSatID(id),P.time_s(id));
                else
                    obj.Detail.String=sprintf(['Packet %d | %s | GS -> satellite %d\nGenerated %.6f s | Arrival %.6f s | Latency %.3f ms | Deadline %.6f s\n' ...
                        'Cause: %s | Loss location: %s | Loss time %.6f s | SNR %.2f dB | PER %.6g'], ...
                        id,P.finalStatus(id),P.servingSatID(id),P.time_s(id),P.arrivalTime_s(id),P.latency_ms(id), ...
                        P.deadlineTime_s(id),P.lossCause(id),P.lossLocation(id),P.lossTime_s(id),P.snr_dB(id),P.phyPER(id));
                end
            end
        end
    end
end
