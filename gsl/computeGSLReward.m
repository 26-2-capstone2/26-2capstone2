function R=computeGSLReward(P,previousStreak,handover,weights)
% Increasing per-loss penalty for bursts, including runs across step boundaries.
validateattributes(previousStreak,{'numeric'},{'scalar','integer','nonnegative','finite'});
assert(height(P)>0 && all(ismember(P.lost,[0 1])) && all(ismember(P.onTime,[0 1])));
assert(all(~(P.lost==1 & P.onTime)),'GSL:RewardOutcomes');
streak=previousStreak;
maxRun=previousStreak;
cost=0;
n=height(P);
for k=1:n
    if P.lost(k)==1
        streak=streak+1;
        maxRun=max(maxRun,streak);
        cost=cost+streak/(streak+n);
    else
        streak=0;
    end
end
R=struct('onTimeFraction',sum(P.onTime)/n,'burstPenalty',cost/n, ...
    'handoverPenalty',double(handover),'trailingLossRun',streak, ...
    'maxLossRunInStep',maxRun);
R.total=weights.onTime*R.onTimeFraction-weights.burst*R.burstPenalty ...
    -weights.handover*R.handoverPenalty;
end
