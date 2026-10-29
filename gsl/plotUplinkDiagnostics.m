function f=plotUplinkDiagnostics(L,P,M,C)
f=figure('Name','GSL Uplink - Channel and Loss Runs','NumberTitle','off', ...
    'Color','w','Tag','GSLCoreResult','Position',[140 60 1100 800]);
tiledlayout(f,3,1);
nexttile; plot(P.time_s,P.snr_dB); ylabel('SNR [dB]'); grid on;
title(sprintf('GSL uplink | %s | experimental assumptions',C.channelScenario),'Interpreter','none');
nexttile; hold on;
scatter(P.time_s(P.onTime),ones(sum(P.onTime),1),2,'k','filled');
scatter(P.time_s(P.lost==1),zeros(sum(P.lost==1),1),6,'r','filled');
scatter(P.time_s(P.late),2*ones(sum(P.late),1),6,[1 .5 0],'filled');
yticks([0 1 2]); yticklabels({'Lost','On time','Late'}); ylim([-.5 2.5]); grid on;
title(sprintf('Loss %.3f%% | On-time %.3f%% | Deadline %.1f ms', ...
    M.packetLossRatio,M.onTimeDeliveryRate_pct,1000*C.gslDeadline_s));
nexttile;
if ~isempty(M.lossRuns)
    stem(M.lossRuns.firstGeneration_s,M.lossRuns.length_packets,'filled');
end
ylabel('Consecutive lost packets'); xlabel('Generation time [s]'); grid on;
title(sprintf('%d loss runs | max %d | mean %.2f packets',M.lossRunCount,M.maxConsecutiveLoss,M.meanConsecutiveLoss));
for ax=findall(f,'Type','axes').', xlim(ax,[0 C.duration_s]); end
if C.exportResults, exportgraphics(f,fullfile(C.outputDir,'uplink_channel_loss_runs.png'),'Resolution',150); end
end
