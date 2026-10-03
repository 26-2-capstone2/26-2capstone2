function R=verify_visualization()
% Real full constellation + actual native viewer + deterministic packet tests.
verify_packets;
C=configGSL(); R=main_gsl_simulation(C); L=R.linkState; M=R.packetMetrics;
assert(numel(R.satellites)==1584 && isequal(size(R.geometry.elevation_deg),[601 1584]));
assert(all(L.servingSatID(L.visibleCount>0)>0));
assert(M.generatedPackets==36000 && M.attemptedPackets==36000 && M.pendingPackets==0);
assert(M.receivedPackets+M.lostPackets==M.generatedPackets);
assert(M.outageLossPackets+M.linkLossPackets==M.lostPackets);
assert(M.packetLossRatio==100*M.lostPackets/M.generatedPackets);
assert(M.totalOutageDuration_s==0 && all(L.residualDoppler_Hz==0));
assert(R.groundStation.ShowLabel && R.groundStation.MarkerSize==20);
f=findall(groot,'Type','figure','Tag','GSLCoreResult'); assert(numel(f)==2);
assert(numel(findall(groot,'Style','pushbutton','String','Play / Resume 3D GSL'))==1);
csv=readtable(fullfile(C.outputDir,'packet_results.csv'));
assert(height(csv)==36000 && sum(csv.outage_loss)+sum(csv.link_loss)==sum(csv.lost));
assert(all(csv.cumulative_received+csv.cumulative_lost==csv.cumulative_generated));
saved=load(fullfile(C.outputDir,'packet_results.mat'));
assert(isequaln(saved.P.lost,R.packetTable.lost) && isequaln(saved.M,R.packetMetrics));
for t=unique([0;L.time_s(L.handoverEvent);475;476;489;490;600]).'
    old=R.viewerController.ServingIndex; R.viewerController.setTime(t);
    chosen=L.servingSatID(find(L.time_s<=t,1,'last'));
    assert(R.viewerController.ServingIndex==chosen);
    assert(isequal(R.access(chosen).LineColor,[1 0 0]) && R.satellites(chosen).ShowLabel);
    if old>0 && old~=chosen
        assert(isequal(R.satellites(old).MarkerColor,[.65 .7 .8]) && ~R.satellites(old).ShowLabel);
        assert(isequal(R.access(old).LineColor,[0 .85 .15]));
    end
    fprintf('PASS: active link frame t=%g, serving=%d.\n',t,chosen);
end
red=0; for k=1:numel(R.access), red=red+isequal(R.access(k).LineColor,[1 0 0]); end
assert(red==1);
R.viewerController.setTime(0);
short=R; short.linkState=R.linkState(1:3,:); playGSL(short);
assert(R.viewerController.StateIndex==3);
R.viewerController.setTime(0);
fprintf('PASS: 2 figures; playback controls; sequential playback; single active red link and old-color reset.\n');
fprintf('PASS: full CSV accounting; 36000 packets; handovers=%d; reference SNR range %.3f..%.3f dB.\n', ...
    sum(L.handoverEvent),min(L.snr_dB),max(L.snr_dB));
% A small REAL geometry scenario with a 90-degree mask exercises actual outage.
E=C; E.numPlanes=4; E.satsPerPlane=6; E.phaseFactor=1; E.duration_s=2;
E.minElevation_deg=90; E.makePlots=false; E.exportResults=false;
edge=main_gsl_simulation(E);
assert(~any(edge.geometry.hasCandidate) && edge.viewerController.ServingIndex==0);
assert(edge.packetMetrics.outageLossPackets==120 && edge.packetMetrics.lostPackets==120);
assert(edge.packetMetrics.packetLossRatio==100 && edge.packetMetrics.totalOutageDuration_s==2);
for k=1:numel(edge.access), assert(~isequal(edge.access(k).LineColor,[1 0 0])); end
assert(contains(edge.viewer.Name,'Outage=1')); delete(edge.viewerController);
fprintf('PASS: REAL no-visible case: serving=none; no red link; 120 outage losses; 2s outage.\n');
if nargout==0, delete(R.viewerController); end
end
