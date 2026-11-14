classdef GSLRLEnvironment < handle
    % One ground station, fixed 8 dB attenuation, one decision per second.
    properties (Constant)
        environmentLoss_dB = 8
        decisionInterval_s = 1
    end

    properties (SetAccess=private)
        rewardWeights
        maxCandidateCount
        totalSatelliteCount
    end

    properties (Access=private)
        config
        geometry
        candidateSNR_dB
        baseCandidateSNR_dB
        snrOffsets_dB
        packetTimes
        packetDraws
        packetBatches
        candidates
        currentSecond
        servingSatID
        lossStreak
        maxLossRun
    end

    methods
        function obj=GSLRLEnvironment(rewardWeights,CFG)
            if nargin<1 || isempty(rewardWeights)
                rewardWeights=struct('onTime',1,'burst',0.5,'handover',0.05);
            end
            for name={'onTime','burst','handover'}
                validateattributes(rewardWeights.(name{1}),{'numeric'}, ...
                    {'scalar','finite','nonnegative'});
            end
            obj.rewardWeights=rewardWeights;
            if nargin<2, CFG=configGSL(); end
            obj.config=CFG;
            cfg=obj.config;
            assert(cfg.channelUpdateStep_s==obj.decisionInterval_s && ...
                cfg.handoverInterruption_s<=obj.decisionInterval_s, 'GSL:RLTimeGrid');
            assert(cfg.channelSigma_dB==0 && cfg.linkDataRate_bps>= ...
                cfg.packetSize_bytes*8*cfg.packetRate_pps, 'GSL:RLPacketModel');
            obj.geometry=buildGSLGeometry(cfg);
            obj.totalSatelliteCount=size(obj.geometry.elevation_deg,2);
            visible=obj.geometry.isVisible(1:end-1,:);
            validateattributes(cfg.candidateCapacity,{'numeric'},{'scalar','integer','positive'});
            validateattributes(cfg.duration_s,{'numeric'},{'scalar','integer','positive'});
            obj.maxCandidateCount=cfg.candidateCapacity;
            ranges=obj.geometry.slantRange_m(1:end-1,:);
            c=299792458;
            % All generated packets resolve before the next decision in this setup.
            delay_s=ranges(visible)/c+cfg.packetSize_bytes*8/cfg.linkDataRate_bps ...
                +cfg.receiverProcessing_s;
            assert(all(delay_s<1/cfg.packetRate_pps),'GSL:RLFeedbackTiming');
            fspl=20*log10(4*pi*ranges(visible)*cfg.carrierFrequency_Hz/c);
            obj.baseCandidateSNR_dB=nan(size(visible));
            obj.baseCandidateSNR_dB(visible)=gslVacuumUplinkSNR(fspl,cfg);
            obj.packetTimes=(0:cfg.duration_s*cfg.packetRate_pps-1).'/cfg.packetRate_pps;
            obj.reset();
        end

        function candidates=reset(obj,packetSeed,snrSeed)
            % Geometry is reused across episodes. Optional seed changes PHY draws.
            if nargin<2, packetSeed=obj.config.packetRandomSeed; end
            if nargin<3, snrSeed=obj.config.snrRandomSeed; end
            obj.snrOffsets_dB=computeGSLRandomSNR(obj.geometry.time_s, ...
                size(obj.geometry.elevation_deg,2),obj.config,snrSeed);
            obj.candidateSNR_dB=obj.baseCandidateSNR_dB+obj.snrOffsets_dB(1:end-1,:) ...
                -obj.environmentLoss_dB;
            stream=RandStream('mt19937ar','Seed',packetSeed);
            obj.packetDraws=rand(stream,numel(obj.packetTimes),1);
            obj.packetBatches=cell(obj.config.duration_s,1);
            obj.currentSecond=0;
            obj.servingSatID=0;
            obj.lossStreak=0;
            obj.maxLossRun=0;
            obj.candidates=obj.makeCandidates();
            candidates=obj.candidates;
        end

        function [next,feedback,done,P]=step(obj,action)
            % Action is a rank in the current table, or 0 when it is empty.
            t=obj.currentSecond;
            cfg=obj.config;
            assert(t<cfg.duration_s,'GSL:RLEpisodeDone','Call reset before stepping again.');
            validateattributes(action,{'numeric'},{'scalar','integer','finite','nonnegative'});
            candidates=obj.candidates;
            assert((isempty(candidates) && action==0) || ...
                (action>=1 && action<=height(candidates)),'GSL:RLInvalidAction', ...
                'Choose an available rank, or 0 when there are no candidates.');
            satID=0;
            if action>0, satID=candidates.satelliteID(action); end
            [next,feedback,done,P]=obj.stepSatelliteID(satID);
        end

        function [next,feedback,done,P]=stepSatelliteID(obj,satelliteID)
            % Stable-ID entry point, also used by full-candidate baselines.
            validateattributes(satelliteID,{'numeric'},{'scalar','integer','finite','nonnegative'});
            t=obj.currentSecond;
            cfg=obj.config;
            assert(t<cfg.duration_s,'GSL:RLEpisodeDone');
            candidates=obj.allCandidates();
            action=find(candidates.satelliteID==satelliteID,1);
            assert((satelliteID==0 && isempty(candidates)) || ~isempty(action), ...
                'GSL:RLInvalidSatelliteID','Select a currently visible satellite ID.');
            if isempty(action), action=0; end
            satID=0; snr=NaN; elevation=NaN; delay_ms=NaN;
            if action>0
                satID=candidates.satelliteID(action);
                snr=candidates.snr_dB(action);
                elevation=candidates.elevation_deg(action);
                delay_ms=1000*obj.geometry.slantRange_m(t+1,satID)/299792458;
            end
            old=obj.servingSatID;
            handover=old>0 && satID>0 && satID~=old;
            L=table([t;t+1],[satID;satID],[satID>0;satID>0],[handover;false], ...
                [snr;snr],[elevation;elevation],[delay_ms;delay_ms], ...
                'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent', ...
                'snr_dB','elevation_deg','propagationDelay_ms'});
            L.gasLoss_dB=zeros(2,1);
            L.cloudLoss_dB=zeros(2,1);
            L.rainLoss_dB=zeros(2,1);
            L.atmosphericLoss_dB=repmat(obj.environmentLoss_dB,2,1);
            L.weatherName=repmat("environment_attenuation",2,1);
            ids=t*cfg.packetRate_pps+(1:cfg.packetRate_pps).';
            P=evaluateGSLPackets(L,cfg,obj.packetTimes(ids),ids,obj.packetDraws(ids));
            P.environmentLoss_dB=repmat(obj.environmentLoss_dB,height(P),1);
            assert(~any(P.outcome_pending),'GSL:RLPendingPackets');
            reward=computeGSLReward(P,obj.lossStreak,handover,obj.rewardWeights);
            obj.lossStreak=reward.trailingLossRun;
            obj.maxLossRun=max(obj.maxLossRun,reward.maxLossRunInStep);
            feedback=struct('startTime_s',t,'stopTime_s',t+1,'servingSatID',satID, ...
                'handover',handover,'generatedPackets',height(P), ...
                'receivedPackets',sum(P.received),'lostPackets',sum(P.lost), ...
                'phyLossPackets',sum(P.phy_loss),'handoverLossPackets',sum(P.handover_loss), ...
                'outageLossPackets',sum(P.outage_loss),'onTimePackets',sum(P.onTime), ...
                'latePackets',sum(P.late),'trailingLossRun',obj.lossStreak, ...
                'maxConsecutiveLoss',obj.maxLossRun);
            feedback.reward=reward.total;
            feedback.rewardDetails=reward;
            obj.packetBatches{t+1}=P;
            obj.servingSatID=satID;
            obj.currentSecond=t+1;
            done=obj.currentSecond==cfg.duration_s;
            obj.candidates=obj.makeCandidates();
            next=obj.candidates;
        end

        function observation=observe(obj)
            % Fixed-size input uses current/past measurements only.
            T=obj.candidates;
            n=height(T);
            features=zeros(obj.maxCandidateCount,6);
            features(1:n,:)=[T.snr_dB/10,T.snrChange_dB,T.elevation_deg/90, ...
                double(T.isServing),double(T.hasSNRHistory),ones(n,1)];
            mask=false(obj.maxCandidateCount,1);
            mask(1:n)=true;
            ids=zeros(obj.maxCandidateCount,1);
            ids(1:n)=T.satelliteID;
            streak=obj.lossStreak/(obj.lossStreak+obj.config.packetRate_pps);
            observation=struct('time_s',obj.currentSecond,'candidateFeatures',features, ...
                'actionMask',mask,'satelliteIDs',ids,'trailingLossRun',obj.lossStreak, ...
                'vector',[features(:);streak]);
        end

        function CFG=configuration(obj)
            CFG=obj.config;
        end

        function [P,M]=results(obj)
            assert(obj.currentSecond==obj.config.duration_s,'GSL:RLIncompleteEpisode', ...
                'Complete the episode before requesting session metrics.');
            P=vertcat(obj.packetBatches{:});
            M=computePacketMetrics(P,obj.config.rollingWindow_s);
        end
    end

    methods
        function T=allCandidates(obj)
            t=obj.currentSecond;
            ids=zeros(0,1); snr=zeros(0,1); elevation=zeros(0,1);
            if t<obj.config.duration_s
                ids=reshape(find(obj.geometry.isVisible(t+1,:)),[],1);
                snr=reshape(obj.candidateSNR_dB(t+1,ids),[],1);
                [~,order]=sortrows([-snr,ids],[1,2]);
                ids=ids(order); snr=snr(order);
                elevation=reshape(obj.geometry.elevation_deg(t+1,ids),[],1);
            end
            change=zeros(numel(ids),1);
            known=false(numel(ids),1);
            if t>0 && t<obj.config.duration_s
                previous=reshape(obj.candidateSNR_dB(t,ids),[],1);
                known=isfinite(previous);
                change(known)=snr(known)-previous(known);
            end
            T=table(repmat(t,numel(ids),1),(1:numel(ids)).',ids,snr,elevation, ...
                ids==obj.servingSatID,'VariableNames',{'time_s','rank','satelliteID', ...
                'snr_dB','elevation_deg','isServing'});
            T.snrChange_dB=change;
            T.hasSNRHistory=known;
            offsets=zeros(numel(ids),1);
            if t<obj.config.duration_s
                offsets=reshape(obj.snrOffsets_dB(t+1,ids),[],1);
            end
            T.snrRandomOffset_dB=offsets;
        end
    end

    methods (Access=private)
        function T=makeCandidates(obj)
            T=obj.allCandidates();
            capacity=obj.maxCandidateCount;
            if height(T)>capacity
                keep=(1:capacity).';
                old=find(T.isServing,1);
                if ~isempty(old) && old>capacity
                    keep(end)=old;
                end
                T=T(keep,:);
                T=sortrows(T,{'snr_dB','satelliteID'},{'descend','ascend'});
            end
            T.rank=(1:height(T)).';
        end
    end
end