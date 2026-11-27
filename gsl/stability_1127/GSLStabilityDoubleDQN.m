classdef GSLStabilityDoubleDQN < handle
    % Shared Q(s,candidate): variable-size action set, no top-K removal.
    properties (SetAccess=private)
        onlineNetwork; targetNetwork; updateCount=0; lastDiagnostics=[];
    end
    properties (Access=private)
        options; stream; states; rewards; nextFeatures; done;
        count=0; cursor=1; avg=[]; avgSq=[]; ages; bestSuccess; seen=0;
    end
    methods
        function obj=GSLStabilityDoubleDQN(O)
            obj.options=O; obj.stream=RandStream('mt19937ar','Seed',O.agentSeed);
            previous=rng; guard=onCleanup(@()rng(previous)); %#ok<NASGU>
            rng(O.agentSeed,'twister');
            obj.onlineNetwork=dlnetwork([featureInputLayer(11,'Normalization','none') ...
                fullyConnectedLayer(64) reluLayer fullyConnectedLayer(64) reluLayer fullyConnectedLayer(1)]);
            obj.targetNetwork=obj.onlineNetwork;
            obj.states=zeros(11,O.replayCapacity,'single');obj.ages=zeros(1,O.replayCapacity);obj.bestSuccess=zeros(1,O.replayCapacity);
            obj.rewards=zeros(1,O.replayCapacity,'single');
            obj.nextFeatures=cell(1,O.replayCapacity); obj.done=false(1,O.replayCapacity);
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
            k=obj.cursor;obj.seen=obj.seen+1;obj.ages(k)=obj.seen;obj.bestSuccess(k)=max(S.features(6,:)); obj.states(:,k)=S.features(:,index); obj.rewards(k)=reward;
            obj.nextFeatures{k}=next.features; obj.done(k)=done;
            obj.cursor=mod(k,obj.options.replayCapacity)+1;
            obj.count=min(obj.count+1,obj.options.replayCapacity);
        end
        function value=learn(obj)
            value=NaN; O=obj.options;
            if obj.count<max(O.batchSize,O.warmupSteps),return;end
            ix=randperm(obj.stream,obj.count,O.batchSize);
            cells=obj.nextFeatures(ix); counts=cellfun(@(x)size(x,2),cells);
            allNext=cat(2,cells{:}); y=obj.rewards(ix); offset=0;targetGap=NaN;
            if ~isempty(allNext)
                x=dlarray(allNext,'CB');
                qo=reshape(extractdata(predict(obj.onlineNetwork,x)),1,[]);
                qt=reshape(extractdata(predict(obj.targetNetwork,x)),1,[]);targetGap=mean(abs(qo-qt));
                for b=1:numel(ix)
                    n=counts(b);
                    if n>0 && ~obj.done(ix(b))
                        [~,j]=max(qo(offset+(1:n)));
                        y(b)=y(b)+O.discountFactor*qt(offset+j);
                    end
                    offset=offset+n;
                end
            end
            [loss,grad]=dlfeval(@GSLStabilityDoubleDQN.modelLoss,obj.onlineNetwork, ...
                dlarray(obj.states(:,ix),'CB'),dlarray(y,'CB'));
            value=double(extractdata(loss)); assert(isfinite(value));
            norm2=0;
            for j=1:height(grad),g=extractdata(grad.Value{j});norm2=norm2+sum(double(g).^2,'all');end
            scale=min(1,O.gradientThreshold/max(sqrt(norm2),eps));grad=dlupdate(@(g)g*scale,grad);
            obj.updateCount=obj.updateCount+1;
            [obj.onlineNetwork,obj.avg,obj.avgSq]=adamupdate(obj.onlineNetwork,grad, ...
                obj.avg,obj.avgSq,obj.updateCount,O.learningRate);
            if O.targetTau>0
                for j=1:height(obj.targetNetwork.Learnables)
                    obj.targetNetwork.Learnables.Value{j}=(1-O.targetTau)*obj.targetNetwork.Learnables.Value{j}+O.targetTau*obj.onlineNetwork.Learnables.Value{j};
                end
            elseif mod(obj.updateCount,O.targetUpdateEvery)==0,obj.targetNetwork=obj.onlineNetwork;end
            obj.lastDiagnostics=[obj.updateCount value sqrt(norm2) scale targetGap ...
                mean(obj.seen-obj.ages(ix)) mean(obj.bestSuccess(ix)<.2) mean(obj.bestSuccess(1:obj.count)<.2)];
        end
        function checkpoint=checkpoint(obj)
            checkpoint=struct('onlineNetwork',obj.onlineNetwork,'targetNetwork',obj.targetNetwork, ...
                'updateCount',obj.updateCount,'options',obj.options,'architecture','shared candidate Q, 11-64-64-1');
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

