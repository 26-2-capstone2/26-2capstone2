function verify_gsl_rl()
% Replay the original selector through the RL API and compare every packet.
verifyReward();
cfg=configGSL();
cfg.initialEnvironmentLoss_dB=8;
cfg.makePlots=false;
cfg.openPacketViewer=false;
cfg.exportResults=false;
baseline=main_gsl_simulation(cfg);
env=GSLRLEnvironment();
candidates=env.reset();
previous=candidates;
for t=0:599
    observation=env.observe();
    assert(numel(observation.vector)==env.maxCandidateCount*6+1);
    assert(all(isfinite(observation.vector)) && sum(observation.actionMask)==height(candidates));
    assert(isequal(observation.satelliteIDs(observation.actionMask),candidates.satelliteID));
    assert(all(observation.candidateFeatures(~observation.actionMask,:)==0,'all'));
    if t==0
        assert(~any(candidates.hasSNRHistory) && ~any(candidates.snrChange_dB));
    else
        [known,loc]=ismember(candidates.satelliteID,previous.satelliteID);
        assert(isequal(known,candidates.hasSNRHistory));
        assert(isequal(candidates.snrChange_dB(known), ...
            candidates.snr_dB(known)-previous.snr_dB(loc(known))));
        assert(all(candidates.snrChange_dB(~known)==0));
    end
    previous=candidates;
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
    assert(isfinite(feedback.reward) && ...
        feedback.trailingLossRun==feedback.rewardDetails.trailingLossRun);
    assert(isequal(P.packetID,t*60+(1:60).'));
    assert(feedback.servingSatID==expectedID && feedback.handover==baseline.linkState.handoverEvent(t+1));
    assert(feedback.generatedPackets==60 && done==(t==599));
end
[P,M]=env.results();
assert(isempty(candidates));
observation=env.observe();
assert(~any(observation.actionMask));
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

function verifyReward()
w=struct('onTime',1,'burst',0.5,'handover',0.05);
P=table(zeros(60,1),true(60,1),'VariableNames',{'lost','onTime'});
r=computeGSLReward(P,0,false,w);
assert(r.total==1 && r.trailingLossRun==0);
scattered=P;
scattered.lost(1:10:60)=1;
scattered.onTime=scattered.lost==0;
burst=P;
burst.lost(1:6)=1;
burst.onTime=burst.lost==0;
a=computeGSLReward(scattered,0,false,w);
b=computeGSLReward(burst,0,false,w);
assert(a.onTimeFraction==b.onTimeFraction && b.total<a.total);
h=computeGSLReward(P,0,true,w);
assert(abs(h.total-(r.total-w.handover))<1e-12);
late=P;
late.onTime(1)=false;
l=computeGSLReward(late,0,false,w);
assert(l.total<r.total && l.burstPenalty==0);
P.lost(:)=1;
P.onTime(:)=false;
a=computeGSLReward(P,0,false,w);
b=computeGSLReward(P,a.trailingLossRun,false,w);
assert(a.trailingLossRun==60 && b.trailingLossRun==120);
assert(b.total<a.total && b.maxLossRunInStep==120);
assert(abs(b.burstPenalty-mean((61:120)./((61:120)+60)))<1e-12);
disp('PASS SAR reward: scattered versus consecutive loss, cross-step runs, late delivery, handover penalty');
end
