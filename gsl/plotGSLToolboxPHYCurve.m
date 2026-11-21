function plotGSLToolboxPHYCurve(rows,out)
f=figure('Visible','off','Color','w','Position',[100 100 1100 500]);
tiledlayout(f,1,2,'Padding','loose','TileSpacing','loose');
for k=1:2
    nexttile;
    errorbar(rows.ebNo_dB,rows.PER,rows.PER-rows.PER_lower95,rows.PER_upper95-rows.PER,'o-','LineWidth',1.1);
    xlabel('Information E_b/N_0 [dB]'); ylabel('Packet error probability'); grid on; ylim([-.02 1.02]);
    if k==1, xlim([-24 16]); title('Full measured range');
    else, xlim([-.5 2.5]); title('Transition region (95% Wilson intervals)'); end
end
sgtitle(sprintf('QPSK + AR4JA | 160 B | AWGN | %d packets per point',min(rows.packets)),'FontSize',13);
exportgraphics(f,fullfile(out,'phy_curve.png'),'Resolution',160); close(f);
end
