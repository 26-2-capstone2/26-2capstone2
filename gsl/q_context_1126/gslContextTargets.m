function y=gslContextTargets(rewards,done,counts,onlineQ,targetQ,gamma)
% Standard Double DQN: ONLINE argmax, TARGET value, no terminal bootstrap.
y=rewards;offset=0;
assert(sum(counts)==numel(onlineQ)&&numel(onlineQ)==numel(targetQ));
for b=1:numel(rewards)
    n=counts(b);
    if n>0&&~done(b)
        [~,j]=max(onlineQ(offset+(1:n)));y(b)=y(b)+gamma*targetQ(offset+j);
    end
    offset=offset+n;
end
end
