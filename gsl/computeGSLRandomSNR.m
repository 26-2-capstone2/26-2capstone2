function offsets=computeGSLRandomSNR(time_s,satelliteCount,CFG,seed)
% Independent per-satellite, time-correlated Gaussian SNR offsets in dB.
if nargin<4, seed=CFG.snrRandomSeed; end
validateattributes(CFG.snrRandomStd_dB,{'numeric'},{'scalar','nonnegative','finite'});
validateattributes(CFG.snrCorrelation_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(seed,{'numeric'},{'scalar','integer','>=',0,'<=',2^32-1});
offsets=zeros(numel(time_s),satelliteCount);
if CFG.snrRandomStd_dB==0, return; end
stream=RandStream('mt19937ar','Seed',seed);
noise=randn(stream,numel(time_s),satelliteCount);
offsets(1,:)=CFG.snrRandomStd_dB*noise(1,:);
for k=2:numel(time_s)
    rho=exp(-(time_s(k)-time_s(k-1))/CFG.snrCorrelation_s);
    offsets(k,:)=rho*offsets(k-1,:)+ ...
        CFG.snrRandomStd_dB*sqrt(1-rho^2)*noise(k,:);
end
end
