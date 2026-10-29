function C = gslChannel(CFG)
% Reproducible, time-correlated dB impairments; no packet-rate dependence.
validateattributes(CFG.channelStep_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.channelCorrelation_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.channelSigma_dB,{'numeric'},{'scalar','nonnegative','finite'});
assert(ismember(string(CFG.channelScenario),["clear","cloudy","rainy","synthetic_fade"]));
t=(0:CFG.channelStep_s:CFG.duration_s).';
if t(end)<CFG.duration_s, t(end+1)=CFG.duration_s; end
s=RandStream('mt19937ar','Seed',CFG.channelRandomSeed);
if ismember(string(CFG.channelScenario),["clear","cloudy","rainy"])
    C=table(t,zeros(size(t)),zeros(size(t)),'VariableNames',{'time_s','correlatedLoss_dB','testFadeLoss_dB'});
    return;
end
x=zeros(size(t)); x(1)=CFG.channelSigma_dB*randn(s);
for k=2:numel(t)
    a=exp(-(t(k)-t(k-1))/CFG.channelCorrelation_s);
    x(k)=a*x(k-1)+CFG.channelSigma_dB*sqrt(1-a*a)*randn(s);
end
fade=zeros(size(t));
if strcmp(CFG.channelScenario,'synthetic_fade')
    for w=CFG.fadeWindows_s.'
        assert(w(2)>w(1));
        inside=t>=w(1) & t<=w(2);
        fade(inside)=fade(inside)+CFG.fadeDepth_dB*sin(pi*(t(inside)-w(1))/(w(2)-w(1))).^2;
    end
end
C=table(t,x,fade,'VariableNames',{'time_s','correlatedLoss_dB','testFadeLoss_dB'});
end
