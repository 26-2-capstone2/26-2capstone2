function D=reward_components(lost,selected,handovers,C,G,O,observedReward)
% Independently reconstruct the environment reward from packet outcomes.
N=C.packetRate_pps;T=C.duration_s;lost=logical(lost(:));assert(numel(lost)==N*T);
index=(1:numel(lost)).';lastSuccess=cummax(index.*double(~lost));streak=index-lastSuccess;
baseBurst=sum(reshape(min(streak,N*10),N,T),1).'/N^2;
valid=selected>0;latency=nan(T,1);rows=find(valid);
ix=sub2ind(size(G.slantRange_m),rows,selected(valid));
latency(valid)=G.slantRange_m(ix)/299792458+gslPacketInformationBits(C)/C.linkDataRate_bps+C.receiverProcessing_s;
onTime=sum(reshape(~lost,N,T),1).'/N.*(latency<=C.gslDeadline_s);
w=O.rewardWeights;success=w.onTime*onTime;burst=w.burst*baseBurst;ho=w.handover*double(handovers);
reward=success-burst-ho;assert(max(abs(reward-observedReward))<1e-10,'Reward decomposition mismatch');
edge=diff([false;lost;false]);lengths=find(edge==-1)-find(edge==1);
D=struct('success',success,'burstPenalty',burst,'handoverPenalty',ho,'reward',reward, ...
    'baseBurstCost',baseBurst,'lost',sum(lost),'maxRun',max([0;lengths]),'handovers',sum(handovers), ...
    'capActivePackets',sum(streak>N*10));
end
