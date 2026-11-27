function verifyStaticReward()
O=configGSLStaticReward();A=O.rewardDefinitions(1);B=O.rewardDefinitions(2);
assert(computeGSLStudyReward(zeros(60,1),60,false,B)==1);
r=computeGSLStudyReward([(1:6)';zeros(54,1)],54,true,B);
assert(abs(r-(.9-.15*91/(60*144)-.03))<1e-12);
assert(abs(computeGSLStudyReward(ones(60,1)*100,0,true,B)+3.78)<1e-12);
env=createStaticRewardEpisode(O,O.trainingSeeds(1),A);
ref=GSLTrendEpisode(env.config,env.geometry,O,O.trainingSeeds(1));
quad=createStaticRewardEpisode(O,O.trainingSeeds(1),B);
for t=1:600
    S=env.observe();id=S.ids(1);
    [n,r,d]=env.step(id);[n2,r2,d2]=ref.step(id);[n3,~,d3]=quad.step(id);
    assert(abs(r-r2)<1e-10&&isequal(n,n2)&&isequal(n,n3)&&d==d2&&d==d3);
end
assert(isequal(env.loss,ref.loss)&&isequal(env.loss,quad.loss));
assert(isequal(env.draws,quad.draws)&&isequal(env.snr,quad.snr));
assert(any(abs(env.studyRewards-quad.studyRewards)>1e-8));
[P,M]=quad.results();assert(isequal(logical(P.lost),quad.loss)&&M.generatedPackets==36000);
fprintf('Reward formula, clipping, original equivalence, paired physics and full packet reference PASS\n');
end
