function R=run_gsl_toolbox_phy_comparison()
% Paired PHY comparison, same geometry/serving policy/packet draws at 6/8 dB.
% This is the existing main's elevation policy, NOT a DDQN performance claim.
root=fileparts(mfilename('fullpath'));
out=fullfile(root,'results_toolbox_phy',char(datetime('now','Format','yyyyMMdd_HHmmss_SSS')));
mkdir(out); C=configGSL(); C.makePlots=false; C.exportResults=false; C.openPacketViewer=false;
[G,sc,sats,gs,links]=buildGSLGeometry(C); %#ok<ASGLU>
L=computeLinkState(G,sats,C);
summary=table(); cases=cell(2,2);
for a=1:2
    loss=[6 8]; loss=loss(a);
    for m=1:2
        cfg=C; label="JPL + tail assumptions";
        if m==2, cfg=configGSLToolboxPHY(cfg); label="Toolbox measured AWGN"; end
        Q=evaluateGSLAttenuation(L,cfg,loss); P=Q.packetTable; M=Q.packetMetrics;
        assert(M.generatedPackets==36000 && M.pendingPackets==0);
        formula=100*(M.generatedPackets-M.receivedPackets)/M.generatedPackets;
        verified=100*(M.phyLossPackets+M.handoverLossPackets+M.outageLossPackets)/M.generatedPackets;
        assert(abs(formula-verified)<1e-10 && abs(formula-M.packetLossRatio)<1e-10);
        if m==2
            old=cases{a,1}.packetTable;
            assert(isequal(P.snr_dB,old.snr_dB) && isequal(P.servingSatID,old.servingSatID) ...
                && isequal(P.phyRandomDraw,old.phyRandomDraw) && isequal(P.handover_loss,old.handover_loss));
        end
        row=table(loss,label,M.generatedPackets,M.receivedPackets,M.lostPackets,M.packetLossRatio, ...
            M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,sum(L.handoverEvent), ...
            M.phyLossPackets,M.handoverLossPackets,M.outageLossPackets,M.pendingPackets, ...
            verified,100*(sum(P.phyPER(P.attempted))+M.handoverLossPackets+M.outageLossPackets)/height(P), ...
            'VariableNames',{'attenuation_dB','phyModel','generated','received','lost','loss_pct', ...
            'onTime_pct','maxLossRun','handovers','phyLoss','handoverLoss','outageLoss','pending', ...
            'verifiedLoss_pct','expectedLoss_pct'});
        summary=[summary;row]; cases{a,m}=Q; %#ok<AGROW>
        stem=sprintf('attenuation_%ddB_model_%d',loss,m);
        writetable(P,fullfile(out,[stem '_packets.csv']));
        writetable(M.lossRuns,fullfile(out,[stem '_loss_runs.csv']));
        fprintf('%d dB | %s | PLR %.4f%% | on-time %.4f%% | max run %d | PHY %d / HO %d\n', ...
            loss,label,M.packetLossRatio,M.onTimeDeliveryRate_pct,M.maxConsecutiveLoss,M.phyLossPackets,M.handoverLossPackets);
    end
end
writetable(summary,fullfile(out,'comparison.csv'));
R=struct('summary',summary,'cases',{cases},'outputDir',out,'selectionPolicy','Existing main: elevation selection, 4 degree margin');
save(fullfile(out,'comparison.mat'),'R','-v7.3');
f=figure('Color','w','Name','GSL PHY model comparison'); tiledlayout(1,2);
nexttile; bar(reshape(summary.loss_pct,2,2).'); xticklabels({'6 dB','8 dB'});
ylabel('Packet loss [%]'); legend('JPL + tail assumptions','Toolbox measured AWGN','Location','best'); grid on;
nexttile; bar(reshape(summary.maxLossRun,2,2).'); xticklabels({'6 dB','8 dB'});
ylabel('Maximum consecutive packet loss'); grid on;
sgtitle('Paired 600 s PHY comparison | same satellite choices and packet draws | one seed');
exportgraphics(f,fullfile(out,'comparison.png'),'Resolution',160);
fid=fopen(fullfile(root,'results_toolbox_phy','latest_path.txt'),'w'); fprintf(fid,'%s',out); fclose(fid);
disp(summary);
end
