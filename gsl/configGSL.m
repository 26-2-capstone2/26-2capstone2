function CFG = configGSL(weatherName)
if nargin==0, weatherName='clear'; end
% GSL uplink research baseline. RF/channel values below are assumptions.
CFG.startTime = datetime(2026,10,2,0,0,0,'TimeZone','UTC');
CFG.duration_s = 600;
CFG.channelUpdateStep_s = 1;
CFG.earthEquatorialRadius_m = 6378137; % WGS84 semi-major axis
CFG.constellationType = 'iridium';
CFG.orbitReferenceRadius_m = 6371e3; % ISL sphere, separate from GS WGS84 radius
CFG.iridiumPlaneSpacing_deg = 31.6; % exact ISL six-plane preset
CFG.satAltitude_m = 780e3; % matched to ISL iridium preset
CFG.inclination_deg = 86.4;
CFG.numPlanes = 6; % orbital planes
CFG.satsPerPlane = 11; % satellites per plane; 6 x 11 = 66
CFG.candidateCapacity = 13; % fixed trained-network input/output capacity
CFG.snrRandomStd_dB = 1; % experimental Gaussian variation, not calibrated weather
CFG.snrCorrelation_s = 5; % smooth variation between one-second decisions
CFG.snrRandomSeed = 20261115;
CFG.phaseFactor = 0; % ISL initializes the same orbital phase in every plane
CFG.raan0_deg = 0;
CFG.argumentOfLatitude0_deg = 0;
% Temporary inland Korea example, not a surveyed/confirmed research site.
CFG.gsLatitude_deg = 37.0;
CFG.gsLongitude_deg = 128.0;
CFG.gsAltitude_m = 0; % height above WGS84 ellipsoid, not terrain elevation
CFG.gsName = 'GS-demo';
CFG.minElevation_deg = 25;
CFG.enablePackets = true;
CFG.enableWeatherComparison = false; % legacy comparison is not used by default main
CFG.initialEnvironmentLoss_dB = 8; % illustrative assumption, not measured weather
CFG.enableAttenuationSlider = true; % total environment loss; no additional weather stacking
CFG.handoverMargin_deg = 4;
CFG.carrierFrequency_Hz = 14e9;
CFG.linkDirection = 'UPLINK';
CFG.groundTxPower_dBW = 7; % 5.01 W, scenario assumption
CFG.groundTxGain_dBi = 28; % scenario assumption, EIRP = 35 dBW
CFG.satelliteRxGT_dB_per_K = -5; % scenario assumption, not Starlink data
CFG.fixedImplementationLoss_dB = 1;
CFG.clearAirZenithLoss_dB = 0.2; % legacy synthetic_fade ONLY; weather uses ITU layer sum
CFG.channelScenario = char(lower(string(weatherName)));
CFG.weather = weatherProfile(CFG.channelScenario);
CFG.channelStep_s = 0.1;
CFG.channelCorrelation_s = 2;
CFG.channelSigma_dB = 0; % no invented temporal fading in the weather scenarios
CFG.channelRandomSeed = 20261029;
CFG.fadeWindows_s = [180 205; 380 405]; % legacy synthetic_fade only, OFF in all weather runs
CFG.fadeDepth_dB = 10; % legacy artificial fade, OFF in clear/cloudy/rainy
CFG.gslDeadline_s = 0.020; % GSL-only experimental assumption, not ISL deadline
CFG.receiverProcessing_s = 0.001;
CFG.openPacketViewer = true;
CFG.packetDisplayCount = 300;
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
CFG.noiseBandwidth_Hz = 50e6;
CFG.informationBitRate_bps = 50e6;
CFG.phyMappingSource = 'Experimental 50 Mbps information rate, QPSK r=1/2, ideal 50 MHz bandwidth; not measured Starlink';
CFG.highSNRPolicy = 'ZERO_CWER'; % above published support: PER=0 research approximation
CFG.lowSNRPolicy = 'UNIT_CWER';
CFG.modulation = 'QPSK';
CFG.channelCoding = 'CCSDS AR4JA';
CFG.codeRate = 1/2;
CFG.informationBlockLength_bits = 1024;
CFG.handoverInterruption_s = 0.100; % StarTCP APNet 2024 Section 3
CFG.perModelSource = 'JPL IPN 42-184 Figure 14: QPSK AR4JA r=1/2 k=1024';
CFG.debugPlots = false;
CFG.openViewer = false;
CFG.autoPlay3D = false; % Wait at t=0; user starts the 600-second playback
CFG.debug = false;
CFG.viewerPlaybackSpeed = 1; % initial playback speed; adjustable in the panel
CFG.makePlots = true;
CFG.exportResults = true;
CFG.outputDir = fullfile(fileparts(mfilename('fullpath')),'results_attenuation','loss_8.0_dB');
end
