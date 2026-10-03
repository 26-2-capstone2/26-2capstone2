function CFG = configGSL()
% Geometry + Ku-band DOWNLINK reference + simulated UDP packet layer.
CFG.startTime = datetime(2026,10,2,0,0,0,'TimeZone','UTC');
CFG.duration_s = 600;
CFG.channelUpdateStep_s = 1;
CFG.earthEquatorialRadius_m = 6378137; % WGS84 semi-major axis
CFG.satAltitude_m = 550e3; % circular orbital radius minus reference radius
CFG.inclination_deg = 53;
CFG.numPlanes = 72;
CFG.satsPerPlane = 22;
CFG.phaseFactor = 39; % Walker Delta F; NOT an angle in degrees
CFG.raan0_deg = 0;
CFG.argumentOfLatitude0_deg = 0;
% Temporary inland Korea example, not a surveyed/confirmed research site.
CFG.gsLatitude_deg = 37.0;
CFG.gsLongitude_deg = 128.0;
CFG.gsAltitude_m = 0; % height above WGS84 ellipsoid, not terrain elevation
CFG.gsName = 'GS-demo';
CFG.minElevation_deg = 25;
CFG.enablePackets = true;
CFG.handoverMargin_deg = 4;
CFG.carrierFrequency_Hz = 12e9;
CFG.txEIRPDensity_dBW_per_MHz = 12.88;
CFG.rxGT_dB_per_K = 13.7;
% Flat signal PSD; receiver noise bandwidth equals occupied signal bandwidth.
% This ratio is NOT a data rate. Actual RF bandwidth is not yet specified.
CFG.signalToNoiseBandwidthRatio = 1;
CFG.linkDataRate_bps = 50e6;
CFG.packetSize_bytes = 160; % simplified UDP datagram size, excludes IP/L2
CFG.packetRate_pps = 60; % baseline
CFG.stressPacketRate_pps = 60; % additional sensitivity case
CFG.rollingWindow_s = 5;
CFG.packetRandomSeed = 20261003;
CFG.noiseBandwidth_Hz = NaN; % TODO: measured/source-backed receiver noise bandwidth
CFG.informationBitRate_bps = NaN; % TODO: verify whether 50 Mbps is information or coded rate
CFG.phyMappingSource = ''; % required before finite bandwidth/rate can be used
CFG.modulation = 'QPSK';
CFG.channelCoding = 'CCSDS AR4JA';
CFG.codeRate = 1/2;
CFG.informationBlockLength_bits = 1024;
CFG.handoverInterruption_s = 0.100; % StarTCP APNet 2024 Section 3
CFG.perModelSource = 'JPL IPN 42-184 Figure 14: QPSK AR4JA r=1/2 k=1024';
CFG.debugPlots = false;
CFG.openViewer = true;
CFG.autoPlay3D = true; % Run main_gsl_simulation starts synchronized playback
CFG.debug = false;
CFG.viewerPlaybackSpeed = 10; % simulation seconds per wall-clock second
CFG.makePlots = true;
CFG.exportResults = true;
CFG.outputDir = fullfile(fileparts(mfilename('fullpath')),'results_packets');
end
