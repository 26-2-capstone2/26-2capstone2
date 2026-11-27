function auditStaticRewardStudy(folder)
D=load(fullfile(folder,'study.mat'),'R');R=D.R;O=R.options;
a=load(fullfile(folder,'linear_initial.mat'),'initial');b=load(fullfile(folder,'quadratic_initial.mat'),'initial');
assert(isequal(a.initial.onlineNetwork.Learnables,b.initial.onlineNetwork.Learnables));
policies=unique(R.runs.policy,'stable');total=0;
for rep=1:numel(O.evaluationSeeds)
    reference=[];
    for k=1:numel(policies)
        path=fullfile(folder,policies(k),sprintf('repeat_%02d',rep));
        E=load(fullfile(path,'environment.mat'));
        if isempty(reference),reference=E;else
            assert(isequal(reference.G,E.G)&&isequal(reference.snr,E.snr)&&isequaln(reference.per,E.per)&&isequal(reference.draws,E.draws));
        end
        P=readtable(fullfile(path,'packets.csv'));L=readtable(fullfile(path,'decisions.csv'));
        assert(height(P)==36000&&all(P.lost==P.phy_loss+P.handover_loss+P.outage_loss));
        assert(all(P.received+P.lost==1)&&all(P.outcome_pending==0));
        assert(all(abs(L.studyReward(1:600)-(L.onTimeReward(1:600)-L.streakCost(1:600)-L.handoverCost(1:600)))<1e-10));
        streak=0;
        for j=1:height(P)
            if P.lost(j),streak=streak+1;else,streak=0;end
            assert(streak==P.rewardStreak(j));
        end
        total=total+height(P);
    end
end
fprintf('AUDIT PASS: identical initial weights, paired geometry/SNR/PER/draws, %d packet rows, reward components and cross-second streaks\n',total);
end
