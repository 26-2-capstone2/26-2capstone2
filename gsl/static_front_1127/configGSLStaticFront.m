function C=configGSLStaticFront()
gsl=setupGSLStaticFront();C=configGSLToolboxPHY(configGSL());
C.constellationType='static_front_grid';C.numPlanes=6;C.satsPerPlane=11;
C.gridCenterSpeed_mps=0;C.gridPassTime_s=[];
C.initialEnvironmentLoss_dB=6;
C.staticLayoutSeed=20261127;
C.staticHeadingRange_deg=[0 360];
C.staticCrossOffsetFraction=[-.25 .25]; % +/-50km at 200km spacing
C.staticAlongOffsetFraction=[-.25 .25]; % +/-100km at 400km spacing
C.staticFrontColumn=1; % one-based s=1, grid extends toward increasing s
C.snrRandomStd_dB=1;C.snrCorrelation_s=5;
C.makePlots=true;C.exportResults=true;C.openViewer=false;C.openPacketViewer=true;
C.staticBaselineHysteresis_dB=.1;
C.staticDefaultEpisodeSeed=20279401;
C.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_static_front');
assert(isfolder(gsl));
end
