function [id,handover] = selectServingSatellite(elevation_deg,visible,margin_deg)
% Rows=time, columns=stable satellite indices. 0 means no serving satellite.
validateattributes(margin_deg,{'numeric'},{'scalar','nonnegative','finite'});
assert(isequal(size(elevation_deg),size(visible)));
id = zeros(size(elevation_deg,1),1); handover = false(size(id));
old = 0;
for k = 1:numel(id)
    candidates = find(visible(k,:));
    chosen = 0;
    if ~isempty(candidates)
        [~,j] = max(elevation_deg(k,candidates)); % lowest index breaks ties
        best = candidates(j);
        if old==0 || ~visible(k,old)
            chosen = best;
        elseif elevation_deg(k,best)>elevation_deg(k,old)+margin_deg
            chosen = best;
        else
            chosen = old;
        end
    end
    % Acquisition (0->sat) and outage (sat->0) are NOT handovers.
    handover(k) = old>0 && chosen>0 && chosen~=old;
    id(k) = chosen; old = chosen;
end
end
