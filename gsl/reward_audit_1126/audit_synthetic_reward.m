function T=audit_synthetic_reward()
% Formula counterexample only: synthetic packets, not a claimed GSL experiment.
O=configGSLQContext();
A=[true(20,1);repmat([false;true],20,1)];
B=[true(14,1);false;true(13,1);false;true(13,1);false(18,1)];
assert(numel(A)==60&&numel(B)==60&&sum(A)==sum(B));T=table();
for j=1:2
    lost=A;if j==2,lost=B;end
    ix=(1:60).';streak=ix-cummax(ix.*double(~lost));
    success=mean(~lost);cost=mean(min(streak/60,10));
    r=O.rewardWeights.onTime*success-O.rewardWeights.burst*cost;
    row=table(j,sum(lost),max(streak),sum(streak),success,cost,r, ...
        'VariableNames',{'pattern','lostPackets','maxLossRun','sumPacketStreaks','onTimeFraction','burstCost','reward'});
    T=[T;row]; %#ok<AGROW>
end
assert(T.reward(1)>T.reward(2)&&T.maxLossRun(1)>T.maxLossRun(2));
here=fileparts(mfilename('fullpath'));writetable(T,fullfile(here,'synthetic_formula_counterexample.csv'));
disp(T);fprintf('SYNTHETIC CHECK PASS: equal losses, no HO, same second; larger maximum can receive higher reward.\n');
end
