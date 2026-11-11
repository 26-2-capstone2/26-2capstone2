function targets=gslDDQNTargets(rewards,done,nextOnlineQ,nextTargetQ,nextMask,gamma)
% Select with online Q, evaluate the selected action with target Q.
assert(isequal(size(nextOnlineQ),size(nextTargetQ),size(nextMask)));
assert(all(isfinite(nextOnlineQ),'all') && all(isfinite(nextTargetQ),'all'));
mask=logical(nextMask);
% No visible candidate means a forced outage action, encoded in slot 1.
mask(1,~any(mask,1))=true;
q=nextOnlineQ;
q(~mask)=-Inf;
[~,best]=max(q,[],1);
columns=1:size(q,2);
value=nextTargetQ(sub2ind(size(q),best,columns));
targets=single(rewards(:).'+gamma*(~logical(done(:).')).*value);
assert(all(isfinite(targets)));
end
