function [reward,terms]=computeGSLStudyReward(streakVec,numOnTime,isHandover,D)
% streakVec carries across decisions and resets to zero on successful reception.
validateattributes(streakVec,{'numeric'},{'vector','nonnegative','finite'});
n=numel(streakVec);assert(n>0&&numOnTime>=0&&numOnTime<=n);
penalty=mean(min((double(streakVec)/D.L0).^D.power,D.cap));
terms=[D.onTime*numOnTime/n,D.burst*penalty,D.handover*double(isHandover)];
reward=terms(1)-terms(2)-terms(3);
end
