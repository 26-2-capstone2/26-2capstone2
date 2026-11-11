classdef GSLDoubleDQN < handle
    % CPU Double DQN with replay and masked exploration/target selection.
    properties (SetAccess=private)
        onlineNetwork
        targetNetwork
        updateCount=0
    end
    properties (Access=private)
        options
        randomStream
        buffer
        bufferCount=0
        writeIndex=1
        averageGradient=[]
        averageSquaredGradient=[]
    end
    methods
        function obj=GSLDoubleDQN(inputSize,actionCount,O)
            obj.options=O;
            obj.randomStream=RandStream('mt19937ar','Seed',O.agentSeed);
            previous=rng;
            cleanup=onCleanup(@()rng(previous));
            rng(O.agentSeed,'twister');
            layers=[featureInputLayer(inputSize,'Normalization','none')
                fullyConnectedLayer(64)
                reluLayer
                fullyConnectedLayer(64)
                reluLayer
                fullyConnectedLayer(actionCount)];
            obj.onlineNetwork=dlnetwork(layers);
            obj.targetNetwork=obj.onlineNetwork;
            n=O.replayCapacity;
            obj.buffer=struct('states',zeros(inputSize,n,'single'), ...
                'actions',zeros(1,n),'rewards',zeros(1,n,'single'), ...
                'nextStates',zeros(inputSize,n,'single'), ...
                'nextMasks',false(actionCount,n),'done',false(1,n));
        end

        function action=select(obj,observation,epsilon)
            validateattributes(epsilon,{'numeric'},{'scalar','finite','>=',0,'<=',1});
            valid=find(observation.actionMask);
            if isempty(valid)
                action=0;
                return;
            end
            if epsilon>0 && rand(obj.randomStream)<epsilon
                action=valid(randi(obj.randomStream,numel(valid)));
            else
                q=extractdata(predict(obj.onlineNetwork,dlarray(single(observation.vector),'CB')));
                q(~observation.actionMask)=-Inf;
                [~,action]=max(q);
            end
        end

        function remember(obj,state,action,reward,next,done)
            assert((action==0 && ~any(state.actionMask)) || ...
                (action>=1 && action<=numel(state.actionMask) && state.actionMask(action)));
            i=obj.writeIndex;
            obj.buffer.states(:,i)=single(state.vector);
            obj.buffer.actions(i)=max(1,action);
            obj.buffer.rewards(i)=single(reward);
            obj.buffer.nextStates(:,i)=single(next.vector);
            obj.buffer.nextMasks(:,i)=next.actionMask;
            obj.buffer.done(i)=done;
            obj.writeIndex=mod(i,obj.options.replayCapacity)+1;
            obj.bufferCount=min(obj.bufferCount+1,obj.options.replayCapacity);
        end

        function loss=learn(obj)
            loss=NaN;
            if obj.bufferCount<max(obj.options.batchSize,obj.options.warmupSteps)
                return;
            end
            ix=randperm(obj.randomStream,obj.bufferCount,obj.options.batchSize);
            B=obj.buffer;
            x=dlarray(B.nextStates(:,ix),'CB');
            online=extractdata(predict(obj.onlineNetwork,x));
            target=extractdata(predict(obj.targetNetwork,x));
            y=gslDDQNTargets(B.rewards(ix),B.done(ix),online,target, ...
                B.nextMasks(:,ix),obj.options.discountFactor);
            [loss,gradients]=dlfeval(@GSLDoubleDQN.modelLoss,obj.onlineNetwork, ...
                dlarray(B.states(:,ix),'CB'),B.actions(ix),y);
            loss=double(extractdata(loss));
            assert(isfinite(loss),'GSL:DQNLoss');
            normSquared=0;
            for k=1:height(gradients)
                g=extractdata(gradients.Value{k});
                assert(all(isfinite(g),'all'),'GSL:DQNGradient');
                normSquared=normSquared+sum(double(g).^2,'all');
            end
            scale=min(1,obj.options.gradientThreshold/max(sqrt(normSquared),eps));
            gradients=dlupdate(@(g)g*scale,gradients);
            obj.updateCount=obj.updateCount+1;
            [obj.onlineNetwork,obj.averageGradient,obj.averageSquaredGradient]=adamupdate( ...
                obj.onlineNetwork,gradients,obj.averageGradient,obj.averageSquaredGradient, ...
                obj.updateCount,obj.options.learningRate);
            if mod(obj.updateCount,obj.options.targetUpdateEvery)==0
                obj.targetNetwork=obj.onlineNetwork;
            end
        end
    end
    methods (Static,Access=private)
        function [loss,gradients]=modelLoss(net,x,actions,targets)
            q=forward(net,x);
            selector=zeros(size(q),'single');
            selector(sub2ind(size(q),actions,1:numel(actions)))=1;
            chosen=sum(q.*dlarray(selector,'CB'),1);
            error=chosen-dlarray(targets,'CB');
            absolute=abs(error);
            quadratic=min(absolute,1);
            loss=mean(0.5*quadratic.^2+absolute-quadratic,'all');
            gradients=dlgradient(loss,net.Learnables);
        end
    end
end
