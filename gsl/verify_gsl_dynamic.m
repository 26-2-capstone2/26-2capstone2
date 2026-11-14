function verify_gsl_dynamic()
cfg=configGSL(); cfg.constellationType='iridium';
before=rng;
a=computeGSLRandomSNR((0:20).',4,cfg,17);
b=computeGSLRandomSNR((0:20).',4,cfg,17);
c=computeGSLRandomSNR((0:20).',4,cfg,18);
assert(isequal(a,b) && ~isequal(a,c) && ~isequal(a(:,1),a(:,2)));
assert(isequal(before,rng),'GSL:RandomSNRIsolation');
assert(any(diff(a(:,1))~=0));
cfg.snrRandomStd_dB=0;
assert(all(computeGSLRandomSNR((0:20).',4,cfg)==0,'all'));

for count=[1 73 1000]
    cfg=configGSL(); cfg.constellationType='iridium';
    cfg.totalSatellites=count;
    cfg.duration_s=3;
    cfg.candidateCapacity=2;
    cfg.makePlots=false;
    cfg.openPacketViewer=false;
    cfg.exportResults=false;
    env=GSLRLEnvironment([],cfg);
    assert(env.totalSatelliteCount==count);
    initial=env.reset(123,17);
    state=env.observe();
    assert(numel(state.vector)==13 && numel(state.actionMask)==2);
    env.reset(124,17);
    restored=env.allCandidates();
    assert(isequal(initial,restored(1:height(initial),:)));
    env.reset(123,17);
    done=false; snapshots=cell(3,1); second=0;
    while ~done
        second=second+1;
        fullTable=env.allCandidates();
        snapshots{second}=fullTable;
        visible=height(fullTable);
        state=env.observe();
        assert(sum(state.actionMask)==min(visible,2));
        chosen=0;
        if visible>0, chosen=fullTable.satelliteID(end); end
        [next,feedback,done,P]=env.stepSatelliteID(chosen);
        assert(all(P.servingSatID==chosen));
        if chosen>0
            assert(all(P.snr_dB==fullTable.snr_dB(end)));
            following=env.allCandidates();
            if any(following.satelliteID==chosen)
                assert(any(next.satelliteID==chosen),'GSL:RetainOutsideTopK');
            end
        else
            assert(all(P.outage_loss));
        end
        assert(isfinite(feedback.reward));
    end
    [P,M]=env.results();
    assert(height(P)==180 && M.generatedPackets==180 && M.pendingPackets==0);
    assert(abs((180-M.receivedPackets)-(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets))<1e-10);
    env.reset(123,17);
    restored=env.allCandidates();
    assert(isequal(initial,restored(1:height(initial),:)));
    fprintf('PASS exact satellite count %d; fixed capacity; random SNR; ID selection; outage and accounting\n',count);
end

% Full main entry and RL use identical random SNR for the selected satellites.
cfg=configGSL(); cfg.constellationType='iridium'; cfg.totalSatellites=1000; cfg.duration_s=3;
cfg.makePlots=false; cfg.openPacketViewer=false; cfg.exportResults=false;
baseline=main_gsl_simulation(cfg);
env=GSLRLEnvironment([],cfg);
for k=1:3
    [~,~,~,P]=env.stepSatelliteID(baseline.linkState.servingSatID(k));
    ix=(k-1)*60+(1:60);
    assert(isequaln(P,baseline.packetTable(ix,:)),'GSL:MainRandomSNRParity');
end
disp('PASS normal main and RL share the same random SNR and packet outcomes');
end
