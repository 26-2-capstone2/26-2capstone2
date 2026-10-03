function attachGSLPlaybackControls(R)
% Put synchronized playback controls in the existing summary figure.
f=findall(groot,'Type','figure','Name','GSL Session / Handover','Tag','GSLCoreResult');
if isempty(f), return; end
f=f(1); setappdata(f,'GSLPlaying',false);
uicontrol(f,'Style','pushbutton','String','Play / Resume 3D GSL', ...
    'Position',[15 10 180 32],'Callback',@(~,~)playGSL(R,f));
uicontrol(f,'Style','pushbutton','String','Stop', ...
    'Position',[205 10 70 32],'Callback',@(~,~)setappdata(f,'GSLPlaybackStop',true));
uicontrol(f,'Style','text','String','Synchronized playback starts automatically. Stop / Resume here; native playback is disabled.', ...
    'Position',[290 12 650 25],'BackgroundColor','w','HorizontalAlignment','left');
end
