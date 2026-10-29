function f=attachGSLWeatherResults(B,C)
% Add controls to the ORIGINAL performance window; all data already computed.
f=findall(groot,'Type','figure','Tag','GSLCoreResult','Name','UDP SESSION PERFORMANCE');
assert(numel(f)==1,'Expected one original performance figure.');
H=getappdata(f,'GSLPacketPlotHandles'); H.layout.OuterPosition=[0 0 1 .87];
H.layout.TileSpacing='compact'; H.layout.Padding='compact'; H.title.FontSize=12;
setappdata(f,'GSLWeatherCases',B);
names=["clear","cloudy","rainy"]; labels={'맑음 (clear)','흐림 (cloudy)','비 (rainy)'};
uicontrol(f,'Style','text','Units','normalized','Position',[.80 .965 .18 .025], ...
    'String','날씨 선택','BackgroundColor','w','FontSize',11);
popup=uicontrol(f,'Style','popupmenu','Units','normalized','Position',[.80 .925 .18 .035], ...
    'String',labels,'FontSize',11,'Tag','GSLWeatherSelector', ...
    'Value',find(names==string(C.channelScenario)), ...
    'Callback',@(src,~)switchGSLWeather(f,names(src.Value)));
setappdata(f,'GSLWeatherSelector',popup);
lines={'WEATHER    GENERATED   LOST   LOSS(%)   ON-TIME(%)  LATE  MAX-RUN  ATM-LOSS(dB)'};
for j=1:3
    Q=B.(names(j)); M=Q.packetMetrics;
    lines{end+1}=sprintf('%-8s %9d %6d %9.4f %11.4f %5d %8d %13.4f', ...
        names(j),M.generatedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
        M.latePackets,M.maxConsecutiveLoss,mean(Q.linkState.atmosphericLoss_dB,'omitnan')); %#ok<AGROW>
end
annotation(f,'textbox',[.015 .89 .77 .095],'String',lines,'FontName','Consolas', ...
    'FontSize',10,'Interpreter','none','EdgeColor',[.75 .75 .75],'BackgroundColor',[.96 .98 1]);
annotation(f,'textbox',[.80 .885 .18 .035],'String','Same time / no rerun', ...
    'FontSize',10,'EdgeColor','none');
% Export all three cases using these same figure objects, then restore default.
for name=names, switchGSLWeather(f,name,false); end
switchGSLWeather(f,string(C.channelScenario),false);
end
