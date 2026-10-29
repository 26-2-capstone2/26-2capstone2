function B=compareGSLWeather(referenceL,CFG)
% Reuse one geometry/serving schedule; meteorology alone differs between cases.
names=["clear","cloudy","rainy"]; rows=cell(3,1); B=struct;
root=fullfile(fileparts(mfilename('fullpath')),'results_weather');
if isfield(CFG,'weatherOutputDir'), root=CFG.weatherOutputDir; end
if CFG.exportResults && ~isfolder(root), mkdir(root); end
for j=1:3
    C=CFG; C.channelScenario=char(names(j)); C.weather=weatherProfile(names(j));
    C.outputDir=fullfile(root,char(names(j))); C.openViewer=false; C.openPacketViewer=false;
    L=applyGSLWeather(referenceL,C);
    P=simulatePacketTransmission(L,C); M=computePacketMetrics(P,C.rollingWindow_s);
    reportPacketResults(L,P,M,C);
    if C.exportResults
        writetable(L(:,{'time_s','elevation_deg','gasLoss_dB','cloudLoss_dB','rainLoss_dB','atmosphericLoss_dB','snr_dB'}), ...
            fullfile(C.outputDir,'weather_attenuation.csv'));
        fid=fopen(fullfile(C.outputDir,'weather_inputs.json'),'w','n','UTF-8'); assert(fid>=0);
        fprintf(fid,'%s',jsonencode(C.weather,PrettyPrint=true)); fclose(fid);
    end
    B.(names(j))=struct('config',C,'linkState',L,'packetTable',P,'packetMetrics',M);
    rows{j}=table(names(j),C.carrierFrequency_Hz,C.noiseBandwidth_Hz,C.informationBitRate_bps, ...
        C.weather.rainRate_mm_h,C.weather.cloudWaterDensity_g_m3, ...
        M.generatedPackets,M.receivedPackets,M.lostPackets,M.phyLossPackets,M.handoverLossPackets, ...
        M.packetLossRatio,M.onTimeDeliveryRate_pct,M.latePackets,M.maxConsecutiveLoss, ...
        mean(L.atmosphericLoss_dB,'omitnan'),min(P.snr_dB), ...
        'VariableNames',{'weather','carrier_Hz','bandwidth_Hz','informationRate_bps', ...
        'rainRate_mm_h','cloudWater_g_m3','generated','received','lost','phyLost','handoverLost', ...
        'loss_pct','onTime_pct','late','maxConsecutiveLoss','meanAtmosphericLoss_dB','minSNR_dB'});
end
B.summary=vertcat(rows{:});
if CFG.exportResults
    writetable(B.summary,fullfile(root,'weather_comparison.csv'));
    save(fullfile(root,'weather_comparison.mat'),'B','-v7.3');
end
if CFG.makePlots
    f=figure('Name','GSL - Clear / Cloudy / Rainy','NumberTitle','off','Color','w','Position',[80 50 1150 950]);
    tiledlayout(f,4,1);
    nexttile; hold on; for name=names, Q=B.(name); plot(Q.packetTable.time_s,Q.packetTable.snr_dB); end
    ylabel('SNR [dB]'); grid on; legend(names,'Location','best');
    nexttile; hold on; for name=names, Q=B.(name); plot(Q.packetTable.time_s,Q.packetMetrics.rollingOnTimeDeliveryRate_pct); end
    ylabel('On-time [%]'); ylim([0 105]); grid on;
    title('Trailing 5 s, final outcomes by generation time (equal curves overlap)');
    legend(names,'Location','southwest');
    nexttile; bars=bar(categorical(names),[B.summary.loss_pct B.summary.onTime_pct]);
    ylim([0 110]);
    for j=1:numel(bars)
        text(bars(j).XEndPoints,bars(j).YEndPoints+2,compose('%.3f%%',bars(j).YData), ...
            'HorizontalAlignment','center','FontSize',9);
    end
    ylabel('Overall [%]'); legend('Lost','On time','Location','best'); grid on;
    nexttile; hold on; for name=names, Q=B.(name); plot(Q.linkState.time_s,Q.linkState.atmosphericLoss_dB); end
    ylabel('Atmospheric loss [dB]'); xlabel('Generation time [s]'); grid on;
    sgtitle(sprintf('%.1f GHz uplink | %.0f MHz | %.0f Mbps | Deadline %.1f ms | Defined weather conditions, not observations', ...
        CFG.carrierFrequency_Hz/1e9,CFG.noiseBandwidth_Hz/1e6,CFG.informationBitRate_bps/1e6,1000*CFG.gslDeadline_s));
    if CFG.exportResults, exportgraphics(f,fullfile(root,'weather_comparison.png'),'Resolution',140); end
end
disp(B.summary);
end
