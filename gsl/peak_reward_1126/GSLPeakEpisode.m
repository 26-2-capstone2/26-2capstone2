classdef GSLPeakEpisode < GSLContextEpisode
    % Full-episode objectives with sufficient peak/time state, original physics.
    properties (SetAccess=private)
        objectiveRewardHistory;peakIncrements;objectiveOptions;
    end
    methods
        function obj=GSLPeakEpisode(C,G,O,seed)
            obj@GSLContextEpisode(C,G,O,seed);
            obj.objectiveOptions=O;obj.objectiveRewardHistory=zeros(C.duration_s,1);
            obj.peakIncrements=zeros(C.duration_s,1);
        end
        function S=observe(obj)
            S=observe@GSLContextEpisode(obj);n=numel(S.ids);
            peak=max([0;obj.stepMaxRun]);N=obj.config.packetRate_pps;
            extra=single([repmat(peak/(peak+N),1,n);repmat(max(0,1-obj.time/obj.config.duration_s),1,n)]);
            S.features=[S.features;extra];assert(size(S.features,1)==14&&all(isfinite(S.features),'all'));
        end
        function [next,reward,done]=step(obj,id)
            t=obj.time;initialStreak=obj.streak;oldPeak=max([0;obj.stepMaxRun]);
            [~,~,done]=step@GSLContextEpisode(obj,id);
            N=obj.config.packetRate_pps;rows=t*N+(1:N).';lost=obj.loss(rows);
            peak=max([0;obj.stepMaxRun]);increase=peak-oldPeak;
            w=obj.objectiveOptions.rewardWeights;
            if strcmp(obj.objectiveOptions.rewardMode,'peak')
                burst=increase/N;
            else
                s=initialStreak;cost=zeros(N,1);
                for k=1:N,if lost(k),s=s+1;else,s=0;end;cost(k)=min(s/N,10);end
                burst=mean(cost);
            end
            reward=-w.onTime*mean(lost)-w.burst*burst;
            obj.objectiveRewardHistory(t+1)=reward;obj.peakIncrements(t+1)=increase;
            next=obj.observe();
        end
    end
end
