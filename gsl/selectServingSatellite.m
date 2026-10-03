function [id,handover,D] = selectServingSatellite(elevation_deg,visible,margin_deg)
% Rows=time, columns=stable satellite indices. 0 means no serving satellite.
validateattributes(margin_deg,{'numeric'},{'scalar','nonnegative','finite'});
assert(isequal(size(elevation_deg),size(visible)));
id = zeros(size(elevation_deg,1),1); handover = false(size(id));
oldID=id; bestID=id; oldElevation=nan(size(id)); bestElevation=oldElevation;
condition=strings(size(id));
old = 0;
for k = 1:numel(id)
    candidates = find(visible(k,:));
    chosen = 0;
    oldID(k)=old;
    if old>0, oldElevation(k)=elevation_deg(k,old); end
    condition(k)="no_candidates";
    if ~isempty(candidates)
        [~,j] = max(elevation_deg(k,candidates)); % lowest index breaks ties
        best = candidates(j);
        bestID(k)=best; bestElevation(k)=elevation_deg(k,best);
        if old==0 || ~visible(k,old)
            chosen = best;
            condition(k)="acquire_or_old_not_visible";
        elseif best~=old && elevation_deg(k,best)>elevation_deg(k,old)+margin_deg
            chosen = best;
            condition(k)="margin_exceeded";
        else
            chosen = old;
            condition(k)="retain_hysteresis";
        end
    end
    % Acquisition (0->sat) and outage (sat->0) are NOT handovers.
    handover(k) = old>0 && chosen>0 && chosen~=old;
    id(k) = chosen; old = chosen;
end
assert(all(id(any(visible,2))>0),'GSL:ServingInvariant', ...
    'A candidate exists but no serving satellite was selected.');
D=table(sum(visible,2),oldID,bestID,oldElevation,bestElevation,condition,id, ...
    'VariableNames',{'visibleCount','oldServingID','bestCandidateID', ...
    'oldElevation_deg','bestElevation_deg','handoverCondition','servingSatID'});
end
