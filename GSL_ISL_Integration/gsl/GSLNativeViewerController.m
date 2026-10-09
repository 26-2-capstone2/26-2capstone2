classdef GSLNativeViewerController < handle
    % Native R2026a playback. Clock preservation uses the R2026a GlobeViewer bridge.
    % Access has LineColor/LineWidth, no LineStyle.
    % One access per satellite: serving is recolored, never duplicated.
    properties (SetAccess=private)
        Viewer
        ServingIndex = 0
        StateIndex = 0
    end
    properties (Access=private)
        Scenario
        Satellites
        Links
        LinkState
        Updating = false
        LastTime = NaN
        RefreshTimer
        Green = [0 0.85 0.15]
        Red = [1 0 0]
        Gray = [0.65 0.7 0.8]
    end
    methods
        function obj=GSLNativeViewerController(sc,sats,gs,links,L,CFG)
            obj.Scenario=sc; obj.Satellites=sats; obj.Links=links; obj.LinkState=L;
            set(links,'LineColor',obj.Green); set(links,'LineWidth',1);
            set(sats,'MarkerColor',obj.Gray); set(sats,'MarkerSize',3);
            set(sats,'ShowLabel',false);
            gs.Name=sprintf('Ground Station (%s)',CFG.gsName);
            gs.MarkerColor=[1 1 0]; gs.MarkerSize=20;
            gs.LabelFontColor=[1 1 0]; gs.LabelFontSize=18; gs.ShowLabel=true;
            obj.Viewer=satelliteScenarioViewer(sc,'ShowDetails',false, ...
                'Name','3D GSL Environment','PlaybackSpeedMultiplier',CFG.viewerPlaybackSpeed);
            gs.ShowLabel=true; % ShowDetails=false resets labels when the viewer opens.
            show(sats,obj.Viewer); show(gs,obj.Viewer); show(links,obj.Viewer);
            camtarget(obj.Viewer,gs);
            campos(obj.Viewer,CFG.gsLatitude_deg,CFG.gsLongitude_deg,8e6);
            obj.refresh();
            obj.RefreshTimer=timer('ExecutionMode','fixedSpacing','Period',0.1, ...
                'BusyMode','drop','TimerFcn',@(~,~)obj.pollViewer());
            start(obj.RefreshTimer);
        end
        function setTime(obj,time_s)
            % Synchronous entry point for exact sampled frames/handover tests.
            validateattributes(time_s,{'numeric'},{'scalar','finite','nonnegative'});
            assert(time_s<=obj.LinkState.time_s(end),'Time exceeds scenario.');
            obj.Viewer.CurrentTime=obj.Scenario.StartTime+seconds(time_s);
            obj.refresh();
            drawnow;
        end
        function refresh(obj)
            if obj.Updating || ~isvalid(obj.Viewer), return; end
            obj.Updating=true;
            guard=onCleanup(@()obj.unlock()); %#ok<NASGU>
            t=seconds(obj.Viewer.CurrentTime-obj.Scenario.StartTime);
            k=find(obj.LinkState.time_s<=t,1,'last');
            if isempty(k), k=1; end
            chosen=obj.LinkState.servingSatID(k);
            if ~obj.LinkState.isLinkAvailable(k), chosen=0; end
            old=obj.ServingIndex;
            if chosen~=old
                playback=obj.Viewer.GlobeViewer.getPlaybackSpeed();
                before=obj.Viewer.CurrentTime; pause(.02);
                resumeTime=obj.Viewer.CurrentTime;
                wasPlaying=resumeTime>before;

                if old>0
                    obj.Links(old).LineColor=obj.Green; obj.Links(old).LineWidth=1;
                    obj.Satellites(old).MarkerColor=obj.Gray; obj.Satellites(old).MarkerSize=3;
                    obj.Satellites(old).ShowLabel=false;
                end
                if chosen>0
                    obj.Links(chosen).LineColor=obj.Red; obj.Links(chosen).LineWidth=4;
                    obj.Satellites(chosen).MarkerColor=obj.Red; obj.Satellites(chosen).MarkerSize=10;
                    obj.Satellites(chosen).LabelFontColor=obj.Red;
                    obj.Satellites(chosen).ShowLabel=true;
                end
            end
            if chosen~=old && wasPlaying
                % Native style changes stop the clock. Resume at the saved date,
                % retaining its speed; an already paused/seeked viewer stays paused.
                play(obj.Viewer);
                obj.Viewer.GlobeViewer.setDate(resumeTime);
                obj.Viewer.GlobeViewer.setPlaybackSpeed(playback.Speed);
            end
            obj.ServingIndex=chosen; obj.StateIndex=k; obj.LastTime=t;
% Keep the native viewer title fixed; its own timeline displays time.
        end
        function delete(obj)
            obj.stopTimer();
            if ~isempty(obj.Viewer) && isvalid(obj.Viewer), delete(obj.Viewer); end
        end
    end
    methods (Access=private)
        function pollViewer(obj)
            if ~isvalid(obj.Viewer), obj.stopTimer(); return; end
            obj.refresh();
        end
        function stopTimer(obj)
            if ~isempty(obj.RefreshTimer) && isvalid(obj.RefreshTimer)
                stop(obj.RefreshTimer); delete(obj.RefreshTimer);
            end
        end
        function unlock(obj), obj.Updating=false; end
    end
end