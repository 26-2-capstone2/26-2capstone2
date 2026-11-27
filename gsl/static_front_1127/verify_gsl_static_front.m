function R=verify_gsl_static_front()
C=configGSLStaticFront();seed=C.staticDefaultEpisodeSeed;
globalBefore=rng;
[a,~,G]=createGSLStaticFrontEpisode(seed,C);[b,~,G2]=createGSLStaticFrontEpisode(seed,C);
assert(isequal(globalBefore,rng));assert(isequal(G,G2)&&isequal(a.snr,b.snr));
assert(isequal(G.positionStartECEF_m,G.positionEndECEF_m)&&all(G.velocityECEF_mps==0,'all'));
assert(all(diff(G.elevation_deg)==0,'all')&&all(diff(G.slantRange_m)==0,'all')&&all(diff(G.isVisible)==0,'all'));
assert(all(std(a.snr,0,1)>.1));assert(all(isfinite(a.per(G.isVisible))));
[~,nearest]=min(G.slantRange_m(1,:));assert(G.staticSatellites.column(nearest)==1);
assert(abs(G.layout.centerAlongCoordinate_m)>1.5e6);
for k=1:10
    H=buildGSLStaticFrontGeometry(C,seed+k);
    assert(~isequal(G.positionStartECEF_m,H.positionStartECEF_m));
    assert(all(H.visibleCount>0));
end
for shape=[20 36]
    D=C;D.numPlanes=shape;D.satsPerPlane=shape;H=buildGSLStaticFrontGeometry(D,seed);
    assert(size(H.isVisible,2)==shape^2&&all(H.visibleCount>0));
end
R=run_gsl_static_front(seed,C);M=R.packetMetrics;
assert(M.generatedPackets==36000&&M.pendingPackets==0);
assert(M.lostPackets==M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets);
assert(M.handoverLossPackets==6*sum(R.linkState.handoverEvent));
showGSLStaticFront(R,false);
fprintf('STATIC geometry, random reset, varying SNR, packet accounting and larger grids PASS\n');
end
