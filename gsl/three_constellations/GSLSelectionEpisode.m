classdef GSLSelectionEpisode < handle
    % Fast packet-level GSL engine; same formulas/draws as evaluateGSLPackets.
    properties (SetAccess=private)
        config; geometry; snr; per; draws; time=0; servingID=0;
        streak=0; selected; handovers; rewardHistory;
        loss; received; stepMaxRun;
    end
    properties (Access=private)
        options
    end
    methods
        function obj=GSLSelectionEpisode(C,G,O,seed)
            obj.config=C; obj.geometry=G; obj.options=O;
            offsets=computeGSLRandomSNR(G.time_s,size(G.isVisible,2),C,mod(C.snrRandomSeed+seed,2^32));
            fspl=20*log10(4*pi*G.slantRange_m*C.carrierFrequency_Hz/299792458);
            obj.snr=gslVacuumUplinkSNR(fspl,C)+offsets-O.environmentLoss_dB;
            obj.per=nan(size(obj.snr));
            obj.per(G.isVisible)=getPERfromSNR(obj.snr(G.isVisible),C);
            assert(all(isfinite(obj.per(G.isVisible))),'GSL:CurveNeedsExtension');
            stream=RandStream('mt19937ar','Seed',seed);
            obj.draws=rand(stream,C.duration_s*C.packetRate_pps,1);
            obj.selected=zeros(C.duration_s,1); obj.handovers=false(C.duration_s,1);
            obj.rewardHistory=zeros(C.duration_s,1); obj.stepMaxRun=zeros(C.duration_s,1);
            obj.loss=false(numel(obj.draws),1); obj.received=obj.loss;
        end
        function S=observe(obj)
            C=obj.config; t=obj.time;
            if t>=C.duration_s
                S=struct('ids',zeros(0,1),'features',zeros(10,0),'snr',[],'elevation',[],'delta',[],'hasHistory',[]);return;
            end
            ids=find(obj.geometry.isVisible(t+1,:)).';
            quality=obj.snr(t+1,ids).'; elev=obj.geometry.elevation_deg(t+1,ids).';
            [~,order]=sortrows([-quality,ids],[1 2]); ids=ids(order); quality=quality(order); elev=elev(order);
            serving=ids==obj.servingID; old=find(serving,1);
            oldSNR=0; if ~isempty(old),oldSNR=quality(old);end
            delta=zeros(size(ids)); history=false(size(ids));
            if t>0
                history=obj.geometry.isVisible(t,ids).';
                delta(history)=quality(history)-obj.snr(t,ids(history)).';
            end
            success=1-obj.per(t+1,ids).';
            count=numel(ids);
            features=[quality/10,delta/2,elev/90,double(serving),double(history),success, ...
                repmat(obj.streak/(obj.streak+60),count,1),repmat(oldSNR/10,count,1), ...
                (quality-oldSNR)/5,repmat(count/(C.numPlanes*C.satsPerPlane),count,1)].';
            S=struct('ids',ids,'features',single(features),'snr',quality,'elevation',elev, ...
                'delta',delta,'hasHistory',history);
        end
        function [next,reward,done]=step(obj,id)
            C=obj.config; t=obj.time; S=obj.observe();
            assert((isempty(S.ids)&&id==0)||ismember(id,S.ids),'GSL:InvalidSelection');
            ho=obj.servingID>0 && id>0 && obj.servingID~=id;
            u=(0:C.packetRate_pps-1).'/C.packetRate_pps;
            rows=t*C.packetRate_pps+(1:C.packetRate_pps).';
            if id==0
                lost=true(size(u)); onTime=false(size(u));
            else
                blocked=ho & u<C.handoverInterruption_s-16*eps(max(1,t+1));
                lost=blocked | obj.draws(rows)<obj.per(t+1,id);
                latency=obj.geometry.slantRange_m(t+1,id)/299792458 ...
                    +gslPacketInformationBits(C)/C.linkDataRate_bps+C.receiverProcessing_s;
                assert(latency<1/C.packetRate_pps,'GSL:CausalFeedback');
                onTime=~lost & latency<=C.gslDeadline_s;
            end
            costs=zeros(size(u)); longest=obj.streak;
            for k=1:numel(u)
                if lost(k),obj.streak=obj.streak+1;else,obj.streak=0;end
                longest=max(longest,obj.streak);
                costs(k)=min(obj.streak/C.packetRate_pps,10); % linear, bounded for stability
            end
            w=obj.options.rewardWeights;
            reward=w.onTime*mean(onTime)-w.burst*mean(costs)-w.handover*ho;
            obj.selected(t+1)=id; obj.handovers(t+1)=ho; obj.rewardHistory(t+1)=reward;
            obj.loss(rows)=lost; obj.received(rows)=~lost; obj.stepMaxRun(t+1)=longest;
            obj.servingID=id; obj.time=t+1; done=obj.time==C.duration_s;
            next=obj.observe();
        end
        function [P,M,L]=results(obj)
            C=obj.config; assert(obj.time==C.duration_s);
            ids=[obj.selected;obj.selected(end)]; times=obj.geometry.time_s;
            valid=ids>0; quality=nan(size(ids)); elevation=quality; delay=quality;
            ix=sub2ind(size(obj.snr),find(valid),ids(valid));
            quality(valid)=obj.snr(ix); elevation(valid)=obj.geometry.elevation_deg(ix);
            delay(valid)=1000*obj.geometry.slantRange_m(ix)/299792458;
            L=table(times,ids,valid,[obj.handovers;false],quality,elevation,delay, ...
                'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent', ...
                'snr_dB','elevation_deg','propagationDelay_ms'});
            L.atmosphericLoss_dB=repmat(obj.options.environmentLoss_dB,height(L),1);
            L.gasLoss_dB=zeros(height(L),1);L.cloudLoss_dB=L.gasLoss_dB;L.rainLoss_dB=L.gasLoss_dB;
            L.weatherName=repmat("environment_attenuation",height(L),1);
            t=(0:numel(obj.draws)-1).'/C.packetRate_pps;
            P=evaluateGSLPackets(L,C,t,(1:numel(t)).',obj.draws);
            P.environmentLoss_dB=repmat(obj.options.environmentLoss_dB,height(P),1);
            assert(isequal(logical(P.lost),obj.loss) && isequal(logical(P.received),obj.received), ...
                'GSL:FastReferenceMismatch');
            M=computePacketMetrics(P,C.rollingWindow_s);
            assert(M.pendingPackets==0 && M.generatedPackets-M.receivedPackets== ...
                M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets);
        end
    end
end
