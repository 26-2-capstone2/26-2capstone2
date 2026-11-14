function verify_gsl_link_interface()
C=configGSL(); C.duration_s=4; C.exportResults=false;
env=GSLRLEnvironment([],C);
T=env.allSatelliteStates();
assert(height(T)==66 && isequal(T.satelliteID,(1:66).'));
assert(all(T.satelliteID==T.p*11+T.s+1));
assert(all(isnan(T.snr_dB(~T.isVisible))));
visible=env.allCandidates();
[found,rows]=ismember(visible.satelliteID,T.satelliteID);
assert(all(found) && isequal(visible.snr_dB,T.snr_dB(rows)));
observation=env.observe();
assert(isequal(T.satelliteID(T.inActionSet),sort(observation.satelliteIDs(observation.actionMask))));
invalid=T.satelliteID(find(~T.isVisible,1));
assert(~isempty(invalid));
try
    env.stepSatelliteID(invalid);
    error('GSL:ExpectedIDRejection','Invisible ID was accepted.');
catch e
    assert(strcmp(e.identifier,'GSL:RLInvalidSatelliteID'));
end
unchanged=env.observe(); assert(unchanged.time_s==0);
chosen=visible.satelliteID(1);
[~,f,~,P]=env.stepSatelliteID(chosen);
assert(all(P.servingSatID==chosen) && ~f.handover && f.previousServingSatID==0);
[~,f,~,P]=env.stepSatelliteID(chosen);
assert(~f.handover && f.handoverInterruption_s==0 && all(P.servingSatID==chosen));
visible=env.allCandidates();
newID=visible.satelliteID(find(visible.satelliteID~=chosen,1));
[~,f,~,P]=env.stepSatelliteID(newID);
assert(f.handover && f.previousServingSatID==chosen && f.servingSatID==newID);
assert(f.handoverInterruption_s==0.1 && sum(P.handover_loss)==6);
assert(all(P.snr_dB==visible.snr_dB(visible.satelliteID==newID)));
O=configGSLDQN();
observation=env.observe();
agent=GSLDoubleDQN(numel(observation.vector),env.maxCandidateCount,O);
id=selectGSLDDQNSatelliteID(agent,observation);
assert(ismember(id,observation.satelliteIDs(observation.actionMask)));
[~,f,done,P]=env.stepSatelliteID(id);
assert(done && f.servingSatID==id && all(P.servingSatID==id));
assert(isempty(env.allSatelliteStates()));
disp('PASS stable ID selection, same-ID hold, 100 ms / six-packet handover, full visibility/SNR table, DDQN rank-to-ID adapter');

C.duration_s=2; C.minElevation_deg=90;
env=GSLRLEnvironment([],C);
T=env.allSatelliteStates();
assert(height(T)==66 && ~any(T.isVisible) && all(isnan(T.snr_dB)));
[~,f,~,P]=env.stepSatelliteID(0);
assert(f.outageLossPackets==60 && all(P.outage_loss));
disp('PASS no-visible-satellite ID=0 and explicit invisible SNR masking');

C=configGSL(); C.makePlots=false; C.openPacketViewer=false; C.exportResults=true;
C.outputDir=fullfile(fileparts(pwd),'gsl_id_interface_validation');
R=main_gsl_link_interface([],C);
assert(height(R.satelliteStates)==600*66);
assert(height(R.decisions)==600 && height(R.packetTable)==36000);
assert(R.packetMetrics.receivedPackets==5284);
assert(all(R.decisions.servingSatID>0));
for k=1:600
    T=R.satelliteStates(R.satelliteStates.time_s==k-1 & R.satelliteStates.isVisible,:);
    T=sortrows(T,{'snr_dB','satelliteID'},{'descend','ascend'});
    assert(R.decisions.servingSatID(k)==T.satelliteID(1));
    packetRows=(k-1)*60+(1:60);
    assert(all(R.packetTable.servingSatID(packetRows)==T.satelliteID(1)));
    assert(all(R.packetTable.snr_dB(packetRows)==T.snr_dB(1)));
end
out=readtable(fullfile(R.outputDir,'isl_input_packets.csv'));
assert(height(out)==R.packetMetrics.receivedPackets);
assert(all(out.destinationSatelliteID==out.p*11+out.s+1));
fprintf('PASS 600 external-ID decisions, 36,000 packet IDs, %d delivered ISL packets and full trace CSVs\n',height(out));
end
