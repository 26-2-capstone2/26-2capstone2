classdef GSLBranchEpisode < GSLContextEpisode & matlab.mixin.Copyable
    % All episode properties are value data; copy forks simulator state.
    % No policy or reward changes. Private inherited state is copied too.
    methods
        function obj=GSLBranchEpisode(C,G,O,seed)
            obj@GSLContextEpisode(C,G,O,seed);
        end
    end
end
