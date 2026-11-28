function plot_gsl_burst_audit(out,show)
if nargin<2,show=false;end
visibility='off';if show,visibility='on';end
S=load(fullfile(out,'audit.mat'),'R');R=S.R;
for repeat=[3 10]
    T=readtable(fullfile(out,sprintf('repeat_%02d',repeat),'decisions_with_Q.csv'));
    range=596:599;if repeat==10,range=19:24;end
    T=T(ismember(T.time_s,range),:);
    S=load(fullfile(R.maxsnrRoot,sprintf('repeat_%02d',repeat),'preview.mat'),'preview');P=S.preview.P;
    other=arrayfun(@(t)sum(P.lost(floor(P.time_s)==t)),T.time_s);
    f=figure('Visible',visibility,'Color','w','Position',[60 60 1050 850]);tiledlayout(f,3,1);
    nexttile;plot(T.time_s,T.chosenSNR_dB,'ro-','LineWidth',1.2);hold on;
    plot(T.time_s,T.bestSNR_dB,'bo--','LineWidth',1.2);grid on;ylabel('SNR [dB]');
    legend({'DDQN chosen','Best visible SNR'},'Location','best');
    for k=1:height(T),text(T.time_s(k),T.chosenSNR_dB(k),sprintf(' ID %d',T.chosenID(k)),'VerticalAlignment','top');end
    xlim([min(T.time_s)-.1 max(T.time_s)+.25]);
    nexttile;plot(T.time_s,100*T.chosenPER,'ro-');hold on;plot(T.time_s,100*T.bestPER,'bo--');
    ylim([0 105]);grid on;ylabel('PHY PER [%]');legend({'Chosen','Best SNR alternative'},'Location','best');
    nexttile;bar(T.time_s,[T.actualLossCount,other]);grid on;ylabel('Lost packets / second');xlabel('Time [s]');
    legend({'Original DDQN','Original Max-SNR'},'Location','best');ylim([0 65]);
    sgtitle(sprintf('Repeat %02d | frozen exact replay | no Q-margin blocks in this window',repeat));
    exportgraphics(f,fullfile(out,sprintf('case_repeat_%02d.png',repeat)),'Resolution',160);
    if ~show,close(f);end
end
end
