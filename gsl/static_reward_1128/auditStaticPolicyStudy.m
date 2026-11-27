function auditStaticPolicyStudy(folder)
setupStaticReward();D=load(fullfile(folder,'study.mat'),'R');R=D.R;O=R.options;
assert(O.numEpisodes==100&&height(R.training)==100&&height(R.runs)==30);
assert(numel(O.evaluationSeeds)==10&&isempty(intersect(O.trainingSeeds,O.evaluationSeeds)));
assert(O.maxSNRMargin_dB==0&&O.evaluationQMargins==.02&&strcmp(O.rewardDefinitions.name,'quadratic'));
policies=unique(R.runs.policy,'stable');total=0;
for rep=1:10
    reference=[];
    for k=1:numel(policies)
        path=fullfile(folder,policies(k),sprintf('repeat_%02d',rep));E=load(fullfile(path,'environment.mat'));
        if isempty(reference),reference=E;else
            assert(isequal(reference.G,E.G)&&isequal(reference.snr,E.snr)&&isequaln(reference.per,E.per)&&isequal(reference.draws,E.draws));
        end
        assert(all(diff(E.G.elevation_deg)==0,'all')&&all(diff(E.G.slantRange_m)==0,'all'));
        P=readtable(fullfile(path,'packets.csv'));L=readtable(fullfile(path,'decisions.csv'));
        assert(height(P)==36000&&all(P.lost==P.phy_loss+P.handover_loss+P.outage_loss));
        assert(all(P.received+P.lost==1)&&all(P.outcome_pending==0));
        edges=diff([false;logical(P.lost);false]);lengths=find(edges==-1)-find(edges==1);
        maxrun=0;if ~isempty(lengths),maxrun=max(lengths);end
        row=R.runs(R.runs.policy==policies(k)&R.runs.repeat==rep,:);
        assert(maxrun==row.maxLossRun&&sum(P.lost)==row.lost&&abs(sum(P.onTime)/360-row.onTime_pct)<1e-10);
        assert(sum(P.handover_loss)==6*row.handovers);
        assert(all(abs(L.studyReward(1:600)-(L.onTimeReward(1:600)-L.streakCost(1:600)-L.handoverCost(1:600)))<1e-10));
        for t=1:600
            id=L.servingSatID(t);assert(E.G.isVisible(t,id));
            if policies(k)=="MaxSNR_0dB"
                ids=find(E.G.isVisible(t,:));assert(abs(E.snr(t,id)-max(E.snr(t,ids)))<1e-10);
            elseif startsWith(policies(k),'Elevation')
                ids=find(E.G.isVisible(t,:));assert(abs(E.G.elevation_deg(t,id)-max(E.G.elevation_deg(t,ids)))<1e-10);
            end
        end
        total=total+height(P);
    end
end
fid=fopen(fullfile(folder,'VERIFICATION.txt'),'w');
fprintf(fid,'PASS: static geometry; 100 training episodes; 10 disjoint paired evaluation seeds; %d packet rows; shared layout/SNR/PER/draws; loss accounting; independent max-run and baseline action checks.\n',total);fclose(fid);
fprintf('STATIC POLICY AUDIT PASS: %d paired packet rows\n',total);
end
