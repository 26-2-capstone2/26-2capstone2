classdef GSLStaticRewardEpisode < GSLTrendEpisode
    % Adapt reward only; reuse all existing channel, packet and action physics.
    properties (SetAccess=private)
        studyRewards; rewardTerms; streakSamples;
    end
    properties (Access=private)
        definition;
    end
    methods
        function obj=GSLStaticRewardEpisode(C,G,O,seed,D)
            obj@GSLTrendEpisode(C,G,O,seed);obj.definition=D;
            obj.studyRewards=zeros(C.duration_s,1);obj.rewardTerms=zeros(C.duration_s,3);
            obj.streakSamples=zeros(C.duration_s*C.packetRate_pps,1);
        end
        function [next,reward,done]=step(obj,id)
            t=obj.time;prior=obj.streak;
            [next,original,done]=step@GSLTrendEpisode(obj,id);
            n=obj.config.packetRate_pps;rows=t*n+(1:n);streaks=zeros(n,1);
            for k=1:n
                if obj.loss(rows(k)),prior=prior+1;else,prior=0;end
                streaks(k)=prior;
            end
            assert(prior==obj.streak);
            % Parent reward = on-time fraction - original burst/HO terms.
            % Recover on-time count from exact latency, including deadline failures.
            onTime=0;
            if id>0
                delay=obj.geometry.slantRange_m(t+1,id)/299792458+gslPacketInformationBits(obj.config)/obj.config.linkDataRate_bps+obj.config.receiverProcessing_s;
                onTime=sum(~obj.loss(rows))*(delay<=obj.config.gslDeadline_s);
            end
            [reward,terms]=computeGSLStudyReward(streaks,onTime,obj.handovers(t+1),obj.definition);
            if strcmp(obj.definition.name,'linear'),assert(abs(reward-original)<1e-10);end
            obj.studyRewards(t+1)=reward;obj.rewardTerms(t+1,:)=terms;obj.streakSamples(rows)=streaks;
        end
    end
end
