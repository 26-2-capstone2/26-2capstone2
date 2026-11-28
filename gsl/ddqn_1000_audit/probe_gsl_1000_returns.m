function T=probe_gsl_1000_returns(ddqnRoot,out)
% Diagnostic hindsight replay: change exactly one action, then use frozen DDQN.
S=load(fullfile(ddqnRoot,'study.mat'),'R');O=S.R.options;C=configGSLToolboxPHY(S.R.config);
S=load(fullfile(ddqnRoot,'geometry.mat'),'geometry');G=S.geometry;
S=load(fullfile(ddqnRoot,'agent.mat'),'checkpoint');a=GSLTrendDoubleDQN(O);a.restore(S.checkpoint);
cases=[7 3;7 4;7 5;10 20;10 22];T=table();
for c=1:size(cases,1)
    repeat=cases(c,1);t0=cases(c,2);
    S=load(fullfile(ddqnRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');P=S.preview;
    envs={GSLTrendEpisode(C,G,O,P.seed),GSLTrendEpisode(C,G,O,P.seed)};
    ret=zeros(1,2);q=zeros(1,2);ids=zeros(1,2);suffixLoss=zeros(1,2);suffixMax=zeros(1,2);
    for branch=1:2
        env=envs{branch};
        for t=0:599
            obs=env.observe();ix=a.select(obs,0,O.qHysteresis);
            if t<t0
                assert(obs.ids(ix)==P.L.servingSatID(t+1));
            elseif t==t0
                if branch==2,[~,ix]=max(obs.snr);end
                values=double(a.values(obs));q(branch)=values(ix);ids(branch)=obs.ids(ix);
            end
            [~,r]=env.step(obs.ids(ix));
            if t>=t0,ret(branch)=ret(branch)+O.discountFactor^(t-t0)*r;end
        end
        if branch==1,assert(isequal(env.loss,logical(P.P.lost)));end
        suffix=env.loss(t0*60+1:end);suffixLoss(branch)=sum(suffix);
        edge=diff([false;suffix;false]);runs=find(edge==-1)-find(edge==1);
        suffixMax(branch)=max([0;runs]);
    end
    T=[T;table(repeat,t0,ids(1),ids(2),q(1),q(2),ret(1),ret(2),ret(2)-ret(1), ...
        suffixLoss(1),suffixLoss(2),suffixMax(1),suffixMax(2), ...
        'VariableNames',{'repeat','time_s','chosenID','alternativeID','chosenQ','alternativeQ', ...
        'chosenRealizedDiscountedReturn','alternativeRealizedDiscountedReturn','alternativeMinusChosenReturn', ...
        'chosenSuffixLoss','alternativeSuffixLoss','chosenSuffixMaxRun','alternativeSuffixMaxRun'})]; %#ok<AGROW>
    fprintf('RETURN PROBE %d/%d | repeat=%d t=%d | Q %.5f vs %.5f | realized return %.5f vs %.5f\n', ...
        c,size(cases,1),repeat,t0,q(1),q(2),ret(1),ret(2));
end
writetable(T,fullfile(out,'one_action_counterfactual_returns.csv'));disp(T);
fprintf('Diagnostic only: same realized future channel, not an expected-return proof or proposed online policy.\n');
end
