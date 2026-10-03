function f=attachGSLPlaybackControls(R)
% Visible user-operated controls; main waits at t=0 instead of autoplaying.
f=findall(groot,'Type','figure','Name','GSL Session / Handover','Tag','GSLCoreResult');
if isempty(f)
    f=figure('Name','3D GSL 재생','NumberTitle','off','Color','w', ...
        'Tag','GSLPlaybackControls','Position',[100 80 1050 90]);
else
    f=f(1);
end
setappdata(f,'GSLPlaying',false); setappdata(f,'GSLPlaybackStop',false);
uicontrol(f,'Style','pushbutton','String',sprintf('▶ 재생 / 이어서 (%g초)',R.config.duration_s), ...
    'Tag','GSLPlayButton','Position',[15 10 210 32],'Callback',@(~,~)playGSL(R,f));
uicontrol(f,'Style','pushbutton','String','일시정지', ...
    'Position',[235 10 80 32],'Callback',@(~,~)setappdata(f,'GSLPlaybackStop',true));
uicontrol(f,'Style','text','String','재생 버튼을 누르면 이동을 시작합니다. 빨강: 현재 연결 위성 / 회색: 미연결 위성', ...
    'Tag','GSLPlaybackStatus','Position',[330 12 710 25], ...
    'BackgroundColor','w','HorizontalAlignment','left');
end
