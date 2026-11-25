classdef GSLReplayDoubleDQN < handle
    % Same DDQN network/targets/reward; optional TD-prioritized replay only.
    properties (SetAccess=private)
        onlineNetwork; targetNetwork; updateCount=0
        learningDiagnostics=table();seenCounts=zeros(1,3);sampledCounts=zeros(1,3)
    end
    properties (Access=private)
        options;stream;states;rewards;nextFeatures;done;priorities;
        count=0;cursor=1;avg=[];avgSq=[];
    end
    methods
        function obj=GSLReplayDoubleDQN(O)
            obj.options=O;obj.stream=RandStream('mt19937ar','Seed',O.agentSeed);
            previous=rng;guard=onCleanup(@()rng(previous)); %#ok<NASGU>
            rng(O.agentSeed,'twister');
            obj.onlineNetwork=dlnetwork([featureInputLayer(11,'Normalization','none') ...
                fullyConnectedLayer(64) reluLayer fullyConnectedLayer(64) reluLayer fullyConnectedLayer(1)]);
            obj.targetNetwork=obj.onlineNetwork;
            obj.states=zeros(11,O.replayCapacity,'single');obj.rewards=zeros(1,O.replayCapacity,'single');
            obj.nextFeatures=cell(1,O.replayCapacity);obj.done=false(1,O.replayCapacity);
            obj.priorities=ones(1,O.replayCapacity);
        end
        function q=values(obj,S)
            if isempty(S.ids),q=zeros(1,0);return;end
            q=reshape(extractdata(predict(obj.onlineNetwork,dlarray(S.features,'CB'))),1,[]);
        end
        function index=select(obj,S,epsilon,qMargin)
            if nargin<4,qMargin=0;end
            if isempty(S.ids),index=0;return;end
            if rand(obj.stream)<epsilon,index=randi(obj.stream,numel(S.ids));return;end
            q=obj.values(S);[~,index]=max(q);old=find(S.features(4,:)>0,1);
            if ~isempty(old)&&q(index)<q(old)+qMargin,index=old;end
        end
        function remember(obj,S,index,reward,next,done)
            if index==0,return;end
            k=obj.cursor;obj.states(:,k)=S.features(:,index);obj.rewards(k)=reward;
            obj.nextFeatures{k}=next.features;obj.done(k)=done;
            obj.priorities(k)=max([1 obj.priorities(1:obj.count)]);
            obj.cursor=mod(k,obj.options.replayCapacity)+1;obj.count=min(obj.count+1,obj.options.replayCapacity);
            bin=GSLReplayDoubleDQN.bins(S.features(:,index));obj.seenCounts(bin)=obj.seenCounts(bin)+1;
        end
        function value=learn(obj)
            value=NaN;O=obj.options;
            if obj.count<max(O.batchSize,O.warmupSteps),return;end
            beta=0;
            if strcmp(O.replayMode,'prioritized')
                mass=obj.priorities(1:obj.count).^O.priorityAlpha;prob=mass/sum(mass);
                edges=[0 cumsum(prob)];edges(end)=1;
                ix=discretize(rand(obj.stream,1,O.batchSize),edges);
                beta=O.priorityBetaStart+(1-O.priorityBetaStart)*min(1,obj.updateCount/O.priorityBetaUpdates);
                weights=(obj.count*prob(ix)).^(-beta);
                weights=weights/(obj.count*min(prob))^(-beta);
            else
                ix=randperm(obj.stream,obj.count,O.batchSize);weights=ones(1,O.batchSize);
            end
            assert(all(isfinite(weights))&&all(weights>0)&&all(weights<=1+eps));
            cells=obj.nextFeatures(ix);counts=cellfun(@(x)size(x,2),cells);
            allNext=cat(2,cells{:});y=obj.rewards(ix);offset=0;
            if ~isempty(allNext)
                x=dlarray(allNext,'CB');
                qo=reshape(extractdata(predict(obj.onlineNetwork,x)),1,[]);
                qt=reshape(extractdata(predict(obj.targetNetwork,x)),1,[]);
                for b=1:numel(ix)
                    n=counts(b);
                    if n>0&&~obj.done(ix(b))
                        [~,j]=max(qo(offset+(1:n)));y(b)=y(b)+O.discountFactor*qt(offset+j);
                    end
                    offset=offset+n;
                end
            end
            x=dlarray(obj.states(:,ix),'CB');
            predicted=reshape(extractdata(predict(obj.onlineNetwork,x)),1,[]);
            td=double(y-predicted);
            [loss,grad]=dlfeval(@GSLReplayDoubleDQN.modelLoss,obj.onlineNetwork,x,dlarray(y,'CB'), ...
                dlarray(single(weights),'CB'),strcmp(O.replayMode,'prioritized'));
            value=double(extractdata(loss));assert(isfinite(value));
            norm2=0;
            for j=1:height(grad),g=extractdata(grad.Value{j});norm2=norm2+sum(double(g).^2,'all');end
            scale=min(1,O.gradientThreshold/max(sqrt(norm2),eps));grad=dlupdate(@(g)g*scale,grad);
            obj.updateCount=obj.updateCount+1;
            [obj.onlineNetwork,obj.avg,obj.avgSq]=adamupdate(obj.onlineNetwork,grad, ...
                obj.avg,obj.avgSq,obj.updateCount,O.learningRate);
            if mod(obj.updateCount,O.targetUpdateEvery)==0,obj.targetNetwork=obj.onlineNetwork;end
            if strcmp(O.replayMode,'prioritized')
                uniqueIx=unique(ix);
                for k=uniqueIx,obj.priorities(k)=max(abs(td(ix==k)))+O.priorityEpsilon;end
            end
            bin=GSLReplayDoubleDQN.bins(obj.states(:,ix));bufferBin=GSLReplayDoubleDQN.bins(obj.states(:,1:obj.count));
            for j=1:3,obj.sampledCounts(j)=obj.sampledCounts(j)+sum(bin==j);end
            bad=bin==3;normal=~bad;
            row=table(obj.updateCount,obj.count,mean(bufferBin==3),mean(bad),mean(abs(td)), ...
                mean(abs(td(bad))),mean(abs(td(normal))),beta,min(weights),max(weights), ...
                'VariableNames',{'update','bufferCount','bufferHighPERfraction','sampleHighPERfraction', ...
                'meanAbsTD','highPERmeanAbsTD','otherMeanAbsTD','beta','minISweight','maxISweight'});
            obj.learningDiagnostics=[obj.learningDiagnostics;row];
        end
        function C=coverage(obj)
            C=table(["PER_lt_0.1";"PER_0.1_to_0.9";"PER_ge_0.9"],obj.seenCounts.',obj.sampledCounts.', ...
                'VariableNames',{'regime','seenTransitions','sampledTransitions'});
        end
        function checkpoint=checkpoint(obj)
            checkpoint=struct('onlineNetwork',obj.onlineNetwork,'targetNetwork',obj.targetNetwork, ...
                'updateCount',obj.updateCount,'options',obj.options,'architecture','shared candidate Q, 11-64-64-1');
        end
        function restore(obj,S)
            obj.onlineNetwork=S.onlineNetwork;obj.targetNetwork=S.targetNetwork;obj.updateCount=S.updateCount;
        end
        function D=replaySnapshot(obj)
            D=struct('priorities',obj.priorities(1:obj.count),'count',obj.count, ...
                'classes',GSLReplayDoubleDQN.bins(obj.states(:,1:obj.count)));
        end
    end
    methods (Static,Access=private)
        function b=bins(features)
            per=1-double(features(6,:));b=ones(size(per));b(per>=.1)=2;b(per>=.9)=3;
        end
        function [loss,grad]=modelLoss(net,x,target,weight,prioritized)
            error=forward(net,x)-target;absolute=abs(error);quadratic=min(absolute,1);
            perItem=.5*quadratic.^2+absolute-quadratic;
            if prioritized,loss=mean(weight.*perItem,'all');else,loss=mean(perItem,'all');end
            grad=dlgradient(loss,net.Learnables);
        end
    end
end
