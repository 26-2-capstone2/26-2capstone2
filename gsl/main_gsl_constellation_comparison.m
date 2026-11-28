function main_gsl_constellation_comparison()
% Open saved comparison only; never starts training.
root=fileparts(mfilename('fullpath'));out=fullfile(root,'위성군_비교');
assert(isfile(fullfile(out,'combined_summary.csv')),'Run both studies and generate combined_summary.csv first.');
T=readtable(fullfile(out,'combined_summary.csv'),'TextType','string');
grids=["6x11","20x20","36x36"];policies=["MaxSNR_0dB","Elevation_4deg","quadratic_Q0.02"];
metrics={'loss_pct','maxLossRun','onTime_pct','handovers'};
labels={'Packet loss [%]','Max consecutive loss [packets]','On-time delivery [%]','Handovers'};
for focus=0:1
    p=policies;if focus,p=policies([1 3]);end
    f=figure('Name','Static GSL constellation comparison','Color','w','Position',[70 70 1400 850]);tiledlayout(2,2);
    for j=1:4
        values=zeros(3,numel(p));spread=values;
        for g=1:3
            for k=1:numel(p)
                row=T(T.grid==grids(g)&T.policy==p(k)&T.metric==string(metrics{j}),:);
                assert(height(row)==1);values(g,k)=row.mean;spread(g,k)=row.std;
            end
        end
        nexttile;b=bar(values);hold on;
        for k=1:numel(p),errorbar(b(k).XEndPoints,values(:,k).',spread(:,k).','.k');end
        grid on;xticks(1:3);xticklabels(grids);ylabel(labels{j});
        if focus,legend({'Max SNR','DDQN'},'Location','best');else,legend({'Max SNR','Max elevation','DDQN'},'Location','best');end
    end
    sgtitle('Static grids | 6 dB | 100 DDQN episodes per grid | 10 paired test seeds | mean +/- sample SD');
    name='all_policies';if focus,name='ddqn_vs_maxsnr';end
    exportgraphics(f,fullfile(out,[name '.png']),'Resolution',150);savefig(f,fullfile(out,[name '.fig']));
end
disp(readtable(fullfile(out,'comparison_table.csv')));
disp(readtable(fullfile(out,'candidate_counts.csv')));
end
