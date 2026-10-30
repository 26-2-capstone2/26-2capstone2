function updateGSLAttenuation(f,value)
% Paired comparisons: same original packet IDs, random draws and geometry.
if ~isgraphics(f), return; end
if isappdata(f,'GSLAttenuationBusy') && getappdata(f,'GSLAttenuationBusy'), return; end
setappdata(f,'GSLAttenuationBusy',true);
guard=onCleanup(@()setappdata(f,'GSLAttenuationBusy',false)); %#ok<NASGU>
value=round(value*10)/10;
Q0=getappdata(f,'GSLAttenuationReference');
Q=evaluateGSLAttenuation(Q0.linkState,Q0.config,value);
B=getappdata(f,'GSLWeatherCases'); B.manual=Q; setappdata(f,'GSLWeatherCases',B);
slider=findall(f,'Tag','GSLAttenuationSlider'); slider.Value=value;
label=findall(f,'Tag','GSLEnvironmentValue');
if ~isempty(label), label.String=sprintf('환경 감쇠량: %.1f dB',value); end
switchGSLWeather(f,"manual");
end
