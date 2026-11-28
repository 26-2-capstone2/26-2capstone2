function [env,C,G,O]=createGSLStaticFrontEpisode(episodeSeed,C)
% Use this factory EACH reset: a new layout per seed, time-varying SNR within it.
if nargin<2,C=configGSLStaticFront();end
setupGSLStaticFront();O=configGSLTrendDDQN();O.baseConfig=C;O.environmentLoss_dB=C.initialEnvironmentLoss_dB;
O.geometryMode='static_front_grid';G=buildGSLStaticFrontGeometry(C,episodeSeed);C.candidateCapacity=max(G.visibleCount);
O.baseConfig=C;env=GSLTrendEpisode(C,G,O,episodeSeed);
end
