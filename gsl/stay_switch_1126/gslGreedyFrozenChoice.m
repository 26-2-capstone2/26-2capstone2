function ix=gslGreedyFrozenChoice(agent,S,margin)
% Greedy choice without consuming the agent's exploration/replay RNG.
if isempty(S.ids),ix=0;return;end
q=agent.values(S);[~,ix]=max(q);old=find(S.features(4,:)>0,1);
if ~isempty(old)&&q(ix)<q(old)+margin,ix=old;end
end
