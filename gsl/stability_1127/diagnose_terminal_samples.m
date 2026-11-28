function T=diagnose_terminal_samples()
% Reconstruct ONLY random sampling, not neural-network training.
% Visibility and candidate count are exogenous; inference consumes no agent RNG.
gsl=setupGSLStability();here=fileparts(mfilename('fullpath'));
D=load(fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356/geometry.mat'),'geometry');G=D.geometry;
joined=table();
for capacity=[20000 60000]
    stream=RandStream('mt19937ar','Seed',20261123);done=false(1,capacity);ages=zeros(1,capacity);seen=0;cursor=1;updates=0;record=[];
    for step=1:120000
        second=mod(step-1,600)+1;assert(any(G.isVisible(second,:)));
        epsilon=.05+.95*max(0,1-(step-1)/48000);
        if rand(stream)<epsilon,randi(stream,sum(G.isVisible(second,:)));end
        done(cursor)=mod(step,600)==0;ages(cursor)=step;cursor=mod(cursor,capacity)+1;seen=min(seen+1,capacity);
        if mod(step,8)==0&&seen>=512
            ix=randperm(stream,seen,64);updates=updates+1;
            if mod(updates,100)==0,record(end+1,:)=[step updates sum(done(ix)) mean(step-ages(ix))];end %#ok<AGROW>
        end
    end
    assert(updates==14937);
    if capacity==20000,modes={'low_lr','soft_target'};else,modes={'large_buffer'};end
    for k=1:numel(modes)
        D=readtable(fullfile(here,['results_' modes{k}],'learning_diagnostics.csv'));
        assert(isequal(D.environmentSteps,record(:,1))&&isequal(D.updates,record(:,2)));
        assert(all(abs(D.meanReplayAge_steps-record(:,4))<1e-8),'STABILITY:SamplerRNGMismatch');
        D.terminalSamples=record(:,3);D.mode=repmat(string(modes{k}),height(D),1);
        joined=[joined;D]; %#ok<AGROW>
    end
end
writetable(joined,fullfile(here,'terminal_sample_diagnostics.csv'));T=table();
for mode=["low_lr","large_buffer","soft_target"]
    D=joined(joined.mode==mode & joined.episode>100,:);
    for terminal=[false true]
        A=D((D.terminalSamples>0)==terminal,:);
        row=table(mode,terminal,height(A),mean(A.trainingLoss),median(A.trainingLoss),mean(A.gradientNorm), ...
            sum(A.trainingLoss>.1),'VariableNames',{'mode','containsTerminal','sampledBatches','meanHuberLoss','medianHuberLoss','meanGradientNorm','lossAbovePoint1'});
        T=[T;row]; %#ok<AGROW>
    end
end
writetable(T,fullfile(here,'terminal_sample_summary.csv'));disp(T);
fprintf('TERMINAL SAMPLER RECONSTRUCTION PASS: exact step/update schedules and original RNG API calls, no re-training.\n');
end
