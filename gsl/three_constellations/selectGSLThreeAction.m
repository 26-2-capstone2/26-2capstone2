function index=selectGSLThreeAction(S,policy,O,agent)
if isempty(S.ids),index=0;return;end
if policy=="DDQN"
    index=agent.select(S,0,O.qHysteresis);return;
end
[~,index]=max(S.snr);
if policy=="MaxSNR_Hysteresis"
    old=find(S.features(4,:)>0,1);
    if ~isempty(old) && S.snr(index)<S.snr(old)+O.hysteresis_dB,index=old;end
end
end
