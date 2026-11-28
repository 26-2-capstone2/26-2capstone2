function env=createStaticRewardEpisode(O,seed,D)
C=O.baseConfig;G=buildGSLStaticFrontGeometry(C,seed);C.candidateCapacity=max(G.visibleCount);
env=GSLStaticRewardEpisode(C,G,O,seed,D);
end
