classdef GSLTrendAuditEpisode < GSLTrendEpisode & matlab.mixin.Copyable
    % Exact value-state forks, original 11-input physics and reward unchanged.
    methods
        function obj=GSLTrendAuditEpisode(C,G,O,seed)
            obj@GSLTrendEpisode(C,G,O,seed);
        end
    end
end
