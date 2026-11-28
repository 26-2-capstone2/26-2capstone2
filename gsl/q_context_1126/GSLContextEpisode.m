classdef GSLContextEpisode < GSLTrendEpisode
    % Add one present-time summary of the whole visible action set.
    methods
        function obj=GSLContextEpisode(C,G,O,seed)
            obj@GSLTrendEpisode(C,G,O,seed);
        end
        function S=observe(obj)
            S=observe@GSLTrendEpisode(obj);
            if isempty(S.ids),context=zeros(1,0,'single');
            else,context=repmat(max(S.features(6,:)),1,numel(S.ids));end
            S.features=[S.features;context];
            assert(size(S.features,1)==12&&all(isfinite(S.features),'all'));
        end
    end
end
