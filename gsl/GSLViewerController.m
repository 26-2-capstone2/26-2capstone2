classdef GSLViewerController < handle
    % Public R2026a APIs only. Access has LineColor/LineWidth, no LineStyle.
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
        Green = [0 0.85 0.15]
        Red = [1 0 0]
        Gray = [0.65 0.7 0.8]
    end
    methods
        function obj=GSLViewerController(sc,sats,gs,links,L,CFG)
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
            show(gs,obj.Viewer); show(links,obj.Viewer);
            camtarget(obj.Viewer,gs);
            campos(obj.Viewer,CFG.gsLatitude_deg,CFG.gsLongitude_deg,8e6);
            obj.refresh();
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
            if isequal(t,obj.LastTime), return; end
            k=find(obj.LinkState.time_s<=t,1,'last');
            if isempty(k), k=1; end
            chosen=obj.LinkState.servingSatID(k);
            if ~obj.LinkState.isLinkAvailable(k), chosen=0; end
            old=obj.ServingIndex;
            if chosen~=old
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
            obj.ServingIndex=chosen; obj.StateIndex=k; obj.LastTime=t;
            obj.Viewer.Name=sprintf('3D GSL | t=%.1fs | Serving=%d | Candidates=%d | HO=%d | Outage=%d', ...
                t,chosen,obj.LinkState.visibleCount(k),sum(obj.LinkState.handoverEvent(1:k)),chosen==0);
        end
        function delete(obj)
            if ~isempty(obj.Viewer) && isvalid(obj.Viewer), delete(obj.Viewer); end
        end
    end
    methods (Access=private)
        function unlock(obj), obj.Updating=false; end
    end
end