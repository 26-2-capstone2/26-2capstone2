function verify_gsl_iridium()
C=configGSL(); C.constellationType='iridium';
assert(strcmp(C.constellationType,'iridium') && C.numPlanes==6 && C.satsPerPlane==11);
assert(C.satAltitude_m==780e3 && C.inclination_deg==86.4 && C.iridiumPlaneSpacing_deg==31.6);
C.makePlots=false; C.openPacketViewer=false; C.exportResults=false;
[G,sc,sats]=buildGSLGeometry(C);
assert(numel(sats)==66 && isequal(size(G.elevation_deg),[601 66]));
assert(isequal(G.planeIndex,repelem((0:5).',11)));
assert(isequal(G.satelliteInPlane,repmat((0:10).',6,1)));

radius=C.orbitReferenceRadius_m+C.satAltitude_m;
for k=1:66
    oe=orbitalElements(sats(k));
    assert(abs(oe.SemiMajorAxis-radius)<1);
    assert(abs(oe.Inclination-86.4)<1e-8);
    assert(abs(oe.RightAscensionOfAscendingNode-G.planeIndex(k)*31.6)<1e-8);
    expected=G.satelliteInPlane(k)*360/11+360*C.duration_s/oe.Period; % geometry ends at StopTime
    assert(abs(mod(oe.TrueAnomaly-expected+180,360)-180)<1e-6, ...
        'GSL:IridiumPhase','Satellite %d phase %.9f, expected %.9f',k,oe.TrueAnomaly,expected);
end
fprintf('PASS ISL Iridium preset: 66 satellites, 780 km on 6371 km sphere, 86.4 deg, 31.6 deg planes, matching zero-based IDs\n');
R=main_gsl_simulation(C);
assert(height(R.packetTable)==36000 && R.packetMetrics.pendingPackets==0);
selected=R.packetTable.destinationSatelliteID>0;
P=R.packetTable;
assert(all(P.destinationPlaneIndex(selected)==floor((P.destinationSatelliteID(selected)-1)/11)));
assert(all(P.destinationSatelliteInPlane(selected)==mod(P.destinationSatelliteID(selected)-1,11)));
assert(all(isnan(P.destinationPlaneIndex(~selected))));
env=GSLRLEnvironment([],C);
T=env.reset();
observation=env.observe();
assert(numel(observation.vector)==79);
for k=1:600
    [T,~,~]=env.stepSatelliteID(R.linkState.servingSatID(k));
end
[P,M]=env.results();
assert(isequaln(P,R.packetTable),'GSL:IridiumPacketParity');
fprintf('PASS 600 s main/RL packet parity: loss %.4f%%, on time %.4f%%, outage %.0f packets, max run %d\n', ...
    M.packetLossRatio,M.onTimeDeliveryRate_pct,M.outageLossPackets,M.maxConsecutiveLoss);
end
