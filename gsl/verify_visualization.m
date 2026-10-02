function R=verify_visualization(baselineFile)
% Optional baseline MAT checks that this display-only change preserves results.
verify_packets;
C=configGSL(); C.openViewer=true;
R=main_gsl_simulation(C); L=R.linkState; G=R.geometry;
assert(C.gsLatitude_deg==37 && C.gsLongitude_deg==128 && C.gsAltitude_m==0);
assert(R.groundStation.ShowLabel && R.groundStation.MarkerSize==20);
assert(contains(string(R.groundStation.Name),'Ground Station'));
assert(all(L.servingSatID(G.visibleCount>0)>0));
assert(all(L.servingSatID(L.time_s>=476 & L.time_s<490)==7));
assert(R.packetMetrics.generatedPackets==12000 && R.packetMetrics.transmittedPackets==12000);
assert(isnan(R.packetMetrics.lostPackets));
figs=findall(groot,'Type','figure','Tag','GSLCoreResult');
assert(numel(figs)==3,'Expected exactly three main result figures without PER.');
assert(~isfile(fullfile(C.outputDir,'rolling_packet_loss.png')));
assert(~isfile(fullfile(C.outputDir,'visibility.png')));
if nargin>0
    before=load(baselineFile);
    for name=before.L.Properties.VariableNames
        assert(isequaln(before.L.(name{1}),L.(name{1})),['Regression: ' name{1}]);
    end
    assert(isequaln(before.P.received,R.packetTable.received));
    assert(isequaln(before.P.transmitted,R.packetTable.transmitted));
    assert(isequaln(before.M,R.packetMetrics));
    fprintf('PASS: all pre-existing link-state columns and packet metrics unchanged.\n');
end
% Audit requested interval; no forced repair of serving values.
[~,~,D]=selectServingSatellite(G.elevation_deg,G.isVisible,C.handoverMargin_deg);
D=addvars(D,G.time_s,'Before',1,'NewVariableNames','time_s');
writetable(D(D.time_s>=470 & D.time_s<=492,:),fullfile(C.outputDir,'serving_audit_470_492.csv'));
fprintf('PASS: serving=7 at 476..489 s (not zero); candidate/serving invariant holds for all 601 samples.\n');
for t=unique([0;L.time_s(L.handoverEvent);475;476;489;490;600;0]).'
    old=R.viewerController.ServingIndex;
    R.viewerController.setTime(t);
    fprintf('Checked viewer frame t=%g s.\n',t);
    expected=L.servingSatID(find(L.time_s<=t,1,'last'));
    assert(R.viewerController.ServingIndex==expected);
    assert(isequal(R.access(expected).LineColor,[1 0 0]));
    assert(R.satellites(expected).ShowLabel);
    if old>0 && old~=expected
        assert(isequal(R.access(old).LineColor,[0 0.85 0.15]));
        assert(~R.satellites(old).ShowLabel);
    end
end
% Check the full constellation has only one red access, without duplicate objects.
red=0;
for k=1:numel(R.access), red=red+isequal(R.access(k).LineColor,[1 0 0]); end
assert(red==1 && numel(R.access)==1584);
R.viewer.CurrentTime=R.scenario.StartTime+seconds(476);
R.viewerController.refresh(); drawnow;
assert(R.viewerController.ServingIndex==7);
R.viewerController.setTime(0);
fprintf('PASS: GS marker/label settings; unique red access; all handover frames; explicit refresh after native seek.\n');
fprintf('PASS: 3 main figures; no PER loss figure; 12000 generated/transmitted; GS coordinates unchanged.\n');
if nargout==0
    delete(R.viewerController);
    assert(~isvalid(R.viewer),'Owned viewer did not close with its controller.');
end
end
