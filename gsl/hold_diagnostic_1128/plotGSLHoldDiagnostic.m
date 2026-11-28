function plotGSLHoldDiagnostic(R)
grids=["6x11","20x20","36x36"];policies=["hold_initial","DDQN"];
fields={'loss_pct','meanLength_ge2','maxLength','handovers'};
labels={'패킷 손실률 [%]','평균 연속 손실 길이 [패킷, 2개 이상 구간]','최대 연속 손실 길이 [패킷]','핸드오버 횟수'};
f=figure('Name','진단: 현재 위성 유지 vs DDQN','Color','w','Position',[50 50 1350 850]);tiledlayout(2,2);
for j=1:4
    values=zeros(3,2);spread=values;
    for g=1:3
        for p=1:2
            T=R.summary(R.summary.grid==grids(g)&R.summary.policy==policies(p)&R.summary.metric==string(fields{j}),:);
            values(g,p)=T.mean;spread(g,p)=T.std;
        end
    end
    nexttile;b=bar(values);b(1).FaceColor=[.5 .5 .5];b(2).FaceColor=[.9 .4 .1];hold on;
    for p=1:2,errorbar(b(p).XEndPoints,values(:,p).',spread(:,p).','.k');end
    xticks(1:3);xticklabels(grids);grid on;set(gca,'FontName','Malgun Gothic');ylabel(labels{j},'FontName','Malgun Gothic');
    legend({'첫 선택 위성 600초 유지','DDQN'},'FontName','Malgun Gothic','Location','best');
end
sgtitle({'진단 비교: 첫 위성 유지 vs DDQN — 같은 초기 선택·채널·패킷 난수', ...
    '크기별 10회 평균 ± 표준편차 / 최초 위성 유지 비교만으로 개별 전환의 최적성을 입증하지 않음'},'FontName','Malgun Gothic');
exportgraphics(f,fullfile(R.outputDir,'full_episode_comparison.png'),'Resolution',150);savefig(f,fullfile(R.outputDir,'full_episode_comparison.fig'));
f=figure('Name','DDQN 전환 시점의 1초 강제 유지 진단','Color','w','Position',[80 80 1350 600]);tiledlayout(1,2);
nexttile;T=R.localSummary;
bar([T.DDQN_shorter T.equalPeak T.DDQN_longer],'stacked');xticks(1:3);xticklabels(grids);grid on;
set(gca,'FontName','Malgun Gothic');ylabel('진단 시점 수','FontName','Malgun Gothic');legend({'DDQN이 더 짧음','같음','DDQN이 더 김'},'FontName','Malgun Gothic','Location','best');
title('이후 10초 내 최대 연속 손실 비교','FontName','Malgun Gothic');
nexttile;scatter(R.pairs.hold_peak_10s,R.pairs.DDQN_peak_10s,12,'filled','MarkerFaceAlpha',.3);hold on;
lim=max([R.pairs.hold_peak_10s;R.pairs.DDQN_peak_10s]);plot([0 lim],[0 lim],'k--');axis equal;grid on;
set(gca,'FontName','Malgun Gothic');xlabel('1초 유지 후 DDQN: 최대 길이','FontName','Malgun Gothic');ylabel('원래 DDQN: 최대 길이','FontName','Malgun Gothic');
title('대각선 아래: DDQN 전환이 손실 길이를 줄임','FontName','Malgun Gothic');
sgtitle({'같은 상태에서 전환 vs 1초 강제 유지, 이후 둘 다 DDQN', ...
    '10초 창·직전 연속 손실 포함 / 창이 겹치므로 독립 표본이나 전체 600초 성능으로 해석하지 않음'},'FontName','Malgun Gothic');
exportgraphics(f,fullfile(R.outputDir,'switch_counterfactual.png'),'Resolution',150);savefig(f,fullfile(R.outputDir,'switch_counterfactual.fig'));
end
