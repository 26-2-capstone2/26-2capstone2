function verify_gsl_moving_grid()
C=configGSL();
assert(strcmp(C.constellationType,'moving_grid') && C.numPlanes==6 && C.satsPerPlane==11);
C.makePlots=false; C.openPacketViewer=false; C.exportResults=true;
C.outputDir=fullfile(fileparts(pwd),'gsl_moving_grid_validation');
R=main_gsl_simulation(C);
G=R.geometry; count=numel(R.satellites);
assert(count==66 && isequal(size(G.elevation_deg),[601 66]));
assert(isequal(G.planeIndex,repelem((0:5).',11)));
assert(isequal(G.satelliteInPlane,repmat((0:10).',6,1)));
p0=G.positionStartECEF_m; p1=G.positionEndECEF_m;
radius=C.orbitReferenceRadius_m+C.satAltitude_m;
assert(max(abs(vecnorm(p0)-radius))<1e-5 && max(abs(vecnorm(p1)-radius))<1e-5);
for k=1:count
    d0=vecnorm(p0-p0(:,k));
    d1=vecnorm(p1-p1(:,k));
    assert(max(abs(d0-d1))<1e-5,'GSL:RigidGrid');
end
assert(min(vecnorm(p1-p0))>4e6,'GSL:GridMovement');
T=readtable(fullfile(C.outputDir,'shared_grid_positions.csv'));
L=readtable(fullfile(C.outputDir,'shared_grid_links.csv'));
assert(height(T)==601*66 && height(L)==230);
assert(all(L.toP>=0 & L.toP<6 & L.toS>=0 & L.toS<11));
assert(all(L.islLinkID==L.fromP+6*L.fromS+66*(L.direction-1)));
assert(all(L.fromSatelliteID==11*L.fromP+L.fromS+1));
assert(all(L.toSatelliteID==11*L.toP+L.toS+1));
assert(all(abs(L.propagationDelay_s-L.distance_m/299792458)<1e-12));
assert(numel(unique(L.islLinkID))==230);
assert(max(abs(T.x_ecef_m(1:66)-p0(1,:).'))<1e-5);
delivered=readtable(fullfile(C.outputDir,'isl_input_packets.csv'));
assert(all(delivered.destinationSatelliteID==11*delivered.p+delivered.s+1));
assert(height(delivered)==R.packetMetrics.receivedPackets);
env=GSLRLEnvironment([],C);
assert(env.totalSatelliteCount==66 && env.maxCandidateCount==13);
for k=1:600
    [~,~,~]=env.stepSatelliteID(R.linkState.servingSatID(k));
end
[P,M]=env.results();
assert(isequaln(P,R.packetTable),'GSL:MovingGridPacketParity');
disp(R.candidateDiagnostics.regimeSummary);
disp(R.candidateDiagnostics.policyComparison);
fprintf('PASS rigid moving 6x11 grid, 230 directed ISL neighbors, shared position/packet exports, 600 s main/RL packet parity. Candidate count %d..%d, loss %.4f%%\n', ...
    min(G.visibleCount(1:end-1)),max(G.visibleCount(1:end-1)),M.packetLossRatio);
end
