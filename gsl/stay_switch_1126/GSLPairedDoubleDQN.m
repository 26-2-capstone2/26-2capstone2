classdef GSLPairedDoubleDQN < handle
    % Shared Q(s,candidate): variable-size action set, no top-K removal.
    properties (SetAccess=private)
        onlineNetwork; targetNetwork; updateCount=0
        rareCount=0;lastRareBatchCount=0;rareSamplesUsed=0;normalSamplesUsed=0
    end
    properties (Access=private)
        options; stream; states; rewards; nextFeatures; done;
        count=0; cursor=1; avg=[]; avgSq=[];
        rareStates;rareRewards;rareNext;rareDone;rareCursor=1;
    end
    methods
        function obj=GSLPairedDoubleDQN(O)
            obj.options=O; obj.stream=RandStream('mt19937ar','Seed',O.agentSeed);
            previous=rng; guard=onCleanup(@()rng(previous)); %#ok<NASGU>
            rng(O.agentSeed,'twister');
            reference=GSLTrendDoubleDQN(O);
            obj.onlineNetwork=dlnetwork([featureInputLayer(12,'Normalization','none') ...
                fullyConnectedLayer(64) reluLayer fullyConnectedLayer(64) reluLayer fullyConnectedLayer(1)]);
            parameters=reference.onlineNetwork.Learnables;
            for j=1:height(parameters)
                value=parameters.Value{j};
                if isequal(size(value),[64 11]),value=[value zeros(64,1,'like',value)];end
                obj.onlineNetwork.Learnables.Value{j}=value;
            end
            obj.targetNetwork=obj.onlineNetwork;
            obj.states=zeros(12,O.replayCapacity,'single');
            obj.rewards=zeros(1,O.replayCapacity,'single');
            obj.nextFeatures=cell(1,O.replayCapacity); obj.done=false(1,O.replayCapacity);
            obj.rareStates=zeros(12,O.rareReplayCapacity,'single');obj.rareRewards=zeros(1,O.rareReplayCapacity,'single');
            obj.rareNext=cell(1,O.rareReplayCapacity);obj.rareDone=false(1,O.rareReplayCapacity);
        end
        function q=values(obj,S)
            if isempty(S.ids), q=zeros(1,0);return;end
            q=reshape(extractdata(predict(obj.onlineNetwork,dlarray(S.features,'CB'))),1,[]);
        end
        function index=select(obj,S,epsilon,qMargin)
            if nargin<4,qMargin=0;end
            if isempty(S.ids),index=0;return;end
            if rand(obj.stream)<epsilon
                index=randi(obj.stream,numel(S.ids)); return;
            end
            q=obj.values(S);[~,index]=max(q);
            old=find(S.features(4,:)>0,1);
            if ~isempty(old) && q(index)<q(old)+qMargin,index=old;end
        end
        function remember(obj,S,index,reward,next,done)
            if index==0,return;end
            k=obj.cursor; obj.states(:,k)=S.features(:,index); obj.rewards(k)=reward;
            obj.nextFeatures{k}=next.features; obj.done(k)=done;
            obj.cursor=mod(k,obj.options.replayCapacity)+1;
            obj.count=min(obj.count+1,obj.options.replayCapacity);
        end
        function rememberRare(obj,S,index,reward,next,done)
            k=obj.rareCursor;obj.rareStates(:,k)=S.features(:,index);obj.rareRewards(k)=reward;
            obj.rareNext{k}=next.features;obj.rareDone(k)=done;
            obj.rareCursor=mod(k,obj.options.rareReplayCapacity)+1;
            obj.rareCount=min(obj.rareCount+1,obj.options.rareReplayCapacity);
        end
        function value=learn(obj)
            value=NaN; O=obj.options;
            if obj.count<max(O.batchSize,O.warmupSteps),return;end
            nRare=0;if obj.rareCount>0,nRare=O.rareBatchQuota;end
            nNormal=O.batchSize-nRare;ix=randperm(obj.stream,obj.count,nNormal);
            xStates=obj.states(:,ix);r=obj.rewards(ix);terminal=obj.done(ix);cells=obj.nextFeatures(ix);
            if nRare>0
                ir=randi(obj.stream,obj.rareCount,1,nRare);
                xStates=[xStates obj.rareStates(:,ir)];r=[r obj.rareRewards(ir)];
                terminal=[terminal obj.rareDone(ir)];cells=[cells obj.rareNext(ir)];
            end
            obj.lastRareBatchCount=nRare;obj.rareSamplesUsed=obj.rareSamplesUsed+nRare;
            obj.normalSamplesUsed=obj.normalSamplesUsed+nNormal;
            counts=cellfun(@(x)size(x,2),cells);
            allNext=cat(2,cells{:}); qo=[];qt=[];
            if ~isempty(allNext)
                x=dlarray(allNext,'CB');
                qo=reshape(extractdata(predict(obj.onlineNetwork,x)),1,[]);
                qt=reshape(extractdata(predict(obj.targetNetwork,x)),1,[]);
            end
            y=gslContextTargets(r,terminal,counts,qo,qt,O.discountFactor);
            [loss,grad]=dlfeval(@GSLPairedDoubleDQN.modelLoss,obj.onlineNetwork, ...
                dlarray(xStates,'CB'),dlarray(y,'CB'));
            value=double(extractdata(loss)); assert(isfinite(value));
            norm2=0;
            for j=1:height(grad),g=extractdata(grad.Value{j});norm2=norm2+sum(double(g).^2,'all');end
            scale=min(1,O.gradientThreshold/max(sqrt(norm2),eps));grad=dlupdate(@(g)g*scale,grad);
            obj.updateCount=obj.updateCount+1;
            [obj.onlineNetwork,obj.avg,obj.avgSq]=adamupdate(obj.onlineNetwork,grad, ...
                obj.avg,obj.avgSq,obj.updateCount,O.learningRate);
            if mod(obj.updateCount,O.targetUpdateEvery)==0,obj.targetNetwork=obj.onlineNetwork;end
        end
        function checkpoint=checkpoint(obj)
            checkpoint=struct('onlineNetwork',obj.onlineNetwork,'targetNetwork',obj.targetNetwork, ...
                'updateCount',obj.updateCount,'options',obj.options,'architecture','shared candidate Q with context, 12-64-64-1', ...
                'rareCount',obj.rareCount,'rareSamplesUsed',obj.rareSamplesUsed,'normalSamplesUsed',obj.normalSamplesUsed);
        end
        function restore(obj,S)
            obj.onlineNetwork=S.onlineNetwork;obj.targetNetwork=S.targetNetwork;obj.updateCount=S.updateCount;
        end
    end
    methods (Static,Access=private)
        function [loss,grad]=modelLoss(net,x,target)
            error=forward(net,x)-target; absolute=abs(error);quadratic=min(absolute,1);
            loss=mean(.5*quadratic.^2+absolute-quadratic,'all');grad=dlgradient(loss,net.Learnables);
        end
    end
end


