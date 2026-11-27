function f=showGSLStaticFront(R,showPackets)
if nargin<2,showPackets=false;end
G=R.geometry;T=G.staticSatellites;M=R.packetMetrics;t=G.time_s;
f=figure('Name','GSL Static Front Grid - Varying SNR','Color','w','Position',[80 70 1350 850]);
tiledlayout(2,2,'TileSpacing','compact');
nexttile;scatter(T.alongCoordinate_km,T.crossCoordinate_km,35,[.75 .75 .75],'filled');hold on;
V=T.visible;scatter(T.alongCoordinate_km(V),T.crossCoordinate_km(V),40,[.1 .4 .9],'filled');
plot(0,0,'rp','MarkerSize',18,'MarkerFaceColor','r');
plot(mean(T.alongCoordinate_km),mean(T.crossCoordinate_km),'kx','MarkerSize',12,'LineWidth',2);
for k=1:height(T),text(T.alongCoordinate_km(k)+20,T.crossCoordinate_km(k),string(T.satelliteID(k)),'FontSize',8);end
axis equal;grid on;xlabel('Along grid reference [km]');ylabel('Across grid reference [km]');
title(sprintf('Fixed %dx%d grid | red = GS, x = center | blue = visible',R.config.numPlanes,R.config.satsPerPlane));
nexttile;ids=R.initialCandidates.satelliteID(1:min(4,height(R.initialCandidates)));
plot(t,R.snr(:,ids),'LineWidth',1);grid on;xlabel('Time [s]');ylabel('SNR [dB]');
legend(compose('Satellite %d',ids),'Location','best');title('Same satellites: time-varying SNR, 1 s updates');
nexttile;plot(t,G.elevation_deg(:,ids),'LineWidth',1.5);grid on;xlabel('Time [s]');ylabel('Elevation [deg]');
title('Same satellites: fixed angles throughout the episode');
legend(compose('Satellite %d',ids),'Location','best');
nexttile;plot(R.packetTable.generationTime_s,M.rollingPacketLossRatio,'LineWidth',1);grid on;
xlabel('Time [s]');ylabel('Rolling packet loss [%]');ylim([0 100]);
title(sprintf('Loss %.3f%% | max run %d | handovers %d',M.packetLossRatio,M.maxConsecutiveLoss,sum(R.linkState.handoverEvent)));
sgtitle(sprintf('STATIC geometry | varying SNR | seed %d | %g dB | MaxSNR + %.1f dB (no DDQN)',R.seed,R.config.initialEnvironmentLoss_dB,R.config.staticBaselineHysteresis_dB));
if isfolder(R.outputDir)
    exportgraphics(f,fullfile(R.outputDir,'environment_and_results.png'),'Resolution',150);
    savefig(f,fullfile(R.outputDir,'environment_and_results.fig'));
end
if showPackets,GSLPacketViewer(R.packetTable,R.linkState,R.config,[],R.config.startTime);end
end
