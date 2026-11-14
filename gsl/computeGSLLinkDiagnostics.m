function D=computeGSLLinkDiagnostics(G,Q)
% Evaluate every geometrically visible candidate with the current RF model.
C=Q.config;
loss=C.environmentLoss_dB;
visible=G.isVisible;
offsets=computeGSLRandomSNR(G.time_s,size(visible,2),C);
fspl=20*log10(4*pi*G.slantRange_m*C.carrierFrequency_Hz/299792458);
vacuum=gslVacuumUplinkSNR(fspl,C)+offsets;
snr=vacuum-loss;
snr(~visible)=NaN;
per=nan(size(snr));
per(visible)=getPERfromSNR(snr(visible),C);
[best,bestID]=max(snr,[],2,'omitnan');
worst=min(snr,[],2,'omitnan');
has=any(visible,2);
bestID(~has)=0;
[~,firstVisible]=max(visible,[],2);
missing=has & ~isfinite(best);
bestID(missing)=firstVisible(missing);
n=numel(best);
selectedIndex=find(has);
index=sub2ind(size(snr),selectedIndex,bestID(has));
bestPER=nan(n,1); bestPER(has)=per(index);
unknown=any(visible & ~isfinite(per),2);
unit=has & ~unknown & all(~visible | per==1,2);
possible=has & ~unknown & ~unit;
regime=repmat("NO_VISIBLE_CANDIDATE",n,1);
regime(unit)="ALL_CANDIDATES_PER_ONE";
regime(possible)="SOME_CANDIDATE_PER_BELOW_ONE";
regime(unknown)="UNRESOLVED_PHY";
rows=G.time_s<C.duration_s;
width=diff(G.time_s);
width=width(rows(1:end-1));
times=G.time_s(rows);
counts=sum(visible,2);
horizon=sum(G.elevation_deg>=0,2);
D.perSecond=table(times,horizon(rows),counts(rows),G.maxElevation_deg(rows), ...
    worst(rows),best(rows),Q.linkState.snr_dB(rows),bestID(rows),bestPER(rows),regime(rows), ...
    'VariableNames',{'time_s','aboveHorizonCount','visibleCandidateCount','maxElevation_deg', ...
    'worstCandidateSNR_dB','bestCandidateSNR_dB','selectedSNR_dB','bestSatelliteID','bestCandidatePER','regime'});
names=["NO_VISIBLE_CANDIDATE";"ALL_CANDIDATES_PER_ONE"; ...
    "SOME_CANDIDATE_PER_BELOW_ONE";"UNRESOLVED_PHY"];
duration=zeros(4,1);
for k=1:4
    duration(k)=sum(width(regime(rows)==names(k)));
end
D.regimeSummary=table(names,duration,'VariableNames',{'regime','duration_s'});

% Same seed, packet IDs, RF values and 100 ms switching interruption.
elev=nan(n,1); distance=elev; chosenVacuum=elev;
elev(has)=G.elevation_deg(index);
distance(has)=G.slantRange_m(index);
chosenVacuum(has)=vacuum(index);
ho=[false;bestID(1:end-1)>0 & bestID(2:end)>0 & diff(bestID)~=0];
L=table(G.time_s,bestID,has,ho,elev,1000*distance/299792458,chosenVacuum, ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent', ...
    'elevation_deg','propagationDelay_ms','vacuumSNR_dB'});
L.gasLoss_dB=zeros(n,1); L.cloudLoss_dB=zeros(n,1); L.rainLoss_dB=zeros(n,1);
B=evaluateGSLAttenuation(L,C,loss);
D.bestSNRPackets=B.packetTable;
D.bestSNRMetrics=B.packetMetrics;
metrics={Q.packetMetrics,B.packetMetrics};
policy=["current_elevation_rule";"highest_SNR_each_second"];
received=zeros(2,1); lost=received; plr=received; ontime=received; maxrun=received;
phy=received; handover=received; outage=received;
for k=1:2
    M=metrics{k};
    received(k)=M.receivedPackets; lost(k)=M.lostPackets;
    plr(k)=M.packetLossRatio; ontime(k)=M.onTimeDeliveryRate_pct; maxrun(k)=M.maxConsecutiveLoss;
    phy(k)=M.phyLossPackets; handover(k)=M.handoverLossPackets; outage(k)=M.outageLossPackets;
end
D.policyComparison=table(policy,received,lost,plr,ontime,maxrun,phy,handover,outage, ...
    'VariableNames',{'policy','received','lost','loss_pct','onTime_pct', ...
    'maxConsecutiveLoss','phyLoss','handoverLoss','outageLoss'});
packetRows=discretize(Q.packetTable.time_s,G.time_s);
forced=~has(packetRows) | unit(packetRows);
edges=diff([false;forced;false]); lengths=find(edges==-1)-find(edges==1);
D.unavoidablePackets=sum(forced);
D.unavoidableMaxRun=0;
if ~isempty(lengths), D.unavoidableMaxRun=max(lengths); end
D.environmentLoss_dB=loss;
D.config=C;

% Export only real candidates, indexed by stable satellite ID.
[row,satelliteID]=find(visible & repmat(rows,1,size(visible,2)));
ix=sub2ind(size(snr),row,satelliteID);
D.candidates=table(G.time_s(row),satelliteID,G.elevation_deg(ix), ...
    G.slantRange_m(ix),snr(ix),per(ix), ...
    satelliteID==Q.linkState.servingSatID(row), ...
    'VariableNames',{'time_s','satelliteID','elevation_deg','slantRange_m', ...
    'snr_dB','phyPER','isSelected'});
if isfield(G,'planeIndex')
    D.candidates.planeIndex=G.planeIndex(satelliteID);
    D.candidates.satelliteInPlane=G.satelliteInPlane(satelliteID);
end
D.candidates=sortrows(D.candidates,{'time_s','snr_dB','satelliteID'}, ...
    {'ascend','descend','ascend'});
end
