function satelliteID=selectGSLDDQNSatelliteID(agent,observation)
% Convert this project's DDQN candidate-rank action to a stable satellite ID.
rank=agent.select(observation,0);
if rank==0
    assert(~any(observation.actionMask),'GSL:DDQNMissingAction');
    satelliteID=0;
    return;
end
validateattributes(rank,{'numeric'},{'scalar','integer','positive','finite'});
assert(rank<=numel(observation.satelliteIDs) && observation.actionMask(rank), ...
    'GSL:DDQNInvalidRank');
satelliteID=observation.satelliteIDs(rank);
end
