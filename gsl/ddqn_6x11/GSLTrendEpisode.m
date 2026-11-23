classdef GSLTrendEpisode < GSLSelectionEpisode
    % Add only a causal, continuous-visibility SNR trend to the existing state.
    methods
        function obj=GSLTrendEpisode(C,G,O,seed)
            obj@GSLSelectionEpisode(C,G,O,seed);
        end
        function S=observe(obj)
            S=observe@GSLSelectionEpisode(obj);
            trend=zeros(numel(S.ids),1); samples=trend;
            for j=1:numel(S.ids)
                id=S.ids(j); h=0;
                while h<min(5,obj.time) && obj.geometry.isVisible(obj.time-h,id)
                    h=h+1;
                end
                if h>0
                    trend(j)=(obj.snr(obj.time+1,id)-obj.snr(obj.time+1-h,id))/h;
                end
                samples(j)=h;
            end
            S.trend5_dB_per_s=trend; S.trendHistory_s=samples;
            S.features=[S.features;single(trend.'/2)];
            assert(size(S.features,1)==11 && all(isfinite(S.features),'all'));
        end
    end
end
