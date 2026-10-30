function f=attachGSLAttenuationResults(Q,C)
% One environment slider; no legacy weather table/dropdown or globe.
f=findall(groot,'Type','figure','Name','UDP SESSION PERFORMANCE');
assert(numel(f)==1);
setappdata(f,'GSLWeatherCases',struct('manual',Q));
attachGSLAttenuationSlider(f,struct('clear',Q));
s=findall(f,'Tag','GSLAttenuationSlider'); s.Value=Q.config.environmentLoss_dB;
updateGSLAttenuation(f,s.Value);
end
