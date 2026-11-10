function verify_gsl_rl()
% Replay the original selector through the RL API and compare every packet.
cfg=configGSL();
cfg.initialEnvironmentLoss_dB=8;
cfg.makePlots=false;
cfg.openPacketViewer=false;
cfg.exportResults=false;
baseline=main_gsl_simulation(cfg);
env=GSLRLEnvironment();
candidates=env.reset();
for t=0:599
    expectedID=baseline.linkState.servingSatID(t+1);
    assert(all(diff(candidates.snr_dB)<=0));
    ties=diff(candidates.snr_dB)==0;
    assert(all(diff(candidates.satelliteID)>0 | ~ties));
    assert(isequal(sort(candidates.satelliteID),find(baseline.geometry.isVisible(t+1,:)).'));
    assert(all(candidates.time_s==t));
    if t>0
        assert(isequal(candidates.isServing,candidates.satelliteID==baseline.linkState.servingSatID(t)));
    end
    action=0;
    if expectedID>0
        action=find(candidates.satelliteID==expectedID);
        assert(isscalar(action) && candidates.snr_dB(action)==baseline.linkState.snr_dB(t+1));
    end
    [candidates,feedback,done,P]=env.step(action);
    assert(isequal(P.packetID,t*60+(1:60).'));
    assert(feedback.servingSatID==expectedID && feedback.handover==baseline.linkState.handoverEvent(t+1));
    assert(feedback.generatedPackets==60 && done==(t==599));
end
[P,M]=env.results();
assert(isempty(candidates));
assert(isequaln(P,baseline.packetTable),'GSL:RLBaselinePacketParity');
assert(M.maxConsecutiveLoss==baseline.packetMetrics.maxConsecutiveLoss);
assert(feedback.maxConsecutiveLoss==M.maxConsecutiveLoss);
fprintf('RL baseline PASS: %d packets, %d losses, %.4f%% PLR, %.4f%% on time, max run %d, max candidates %d\n', ...
    M.generatedPackets,M.lostPackets,M.packetLossRatio,M.onTimeDeliveryRate_pct, ...
    M.maxConsecutiveLoss,env.maxCandidateCount);

candidates=env.reset();
assert(height(candidates)>=2);
try
    env.step(height(candidates)+1);
    error('GSL:TestExpectedFailure','Invalid action was accepted.');
catch e
    assert(strcmp(e.identifier,'GSL:RLInvalidAction'));
end
[next,feedback,done,P]=env.step(2);
assert(~done && ~feedback.handover && all(P.servingSatID==candidates.satelliteID(2)));
chosen=next.satelliteID~=candidates.satelliteID(2);
assert(any(chosen));
[~,feedback,~,P]=env.step(find(chosen,1));
assert(feedback.handover && sum(P.handover_loss)==6 && isequal(P.packetID,(61:120).'));
fprintf('RL external action and handover PASS\n');
end
