classdef GSLHoldAuditEpisode < GSLStaticRewardEpisode & matlab.mixin.Copyable
    % State consists of value arrays/structs; forks share no mutable handles.
    methods
        function obj=GSLHoldAuditEpisode(C,G,O,seed,D)
            obj@GSLStaticRewardEpisode(C,G,O,seed,D);
        end
    end
end
