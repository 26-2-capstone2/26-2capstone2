function preview_gsl_toolbox_results()
% Fast review of stored 6/8 dB comparison; no geometry rebuild or PHY retrial.
root=fileparts(mfilename('fullpath'));
path=strtrim(fileread(fullfile(root,'results_toolbox_phy','latest_path.txt')));
S=load(fullfile(path,'comparison.mat'),'R'); Q=S.R.cases{2,2};
Q.config=configGSLToolboxPHY(Q.config); Q.config.makePlots=true; Q.config.exportResults=false;
reportPacketResults(Q.linkState,Q.packetTable,Q.packetMetrics,Q.config);
f=attachGSLAttenuationResults(Q,Q.config);
packet=GSLPacketViewer(Q.packetTable,Q.linkState,Q.config,[],Q.config.startTime);
packet.setTime(600); drawnow;
out=fullfile(root,'results_toolbox_phy','ui_validation');
exportapp(f,fullfile(out,'performance_8dB.png'));
exportapp(packet.Figure,fullfile(out,'packet_viewer_8dB.png'));
fprintf('Stored toolbox results preview ready.\n');
end
