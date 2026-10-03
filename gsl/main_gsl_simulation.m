function R = main_gsl_simulation(CFG)
% Run: R = main_gsl_simulation; then playGSL(R) for synchronized 3D playback.
if nargin == 0, CFG = configGSL(); end
assert(exist('satelliteScenario','file') ~= 0,'GSL:MissingToolbox', ...
    'satelliteScenario requires Aerospace Toolbox or Satellite Communications Toolbox.');
validateattributes(CFG.duration_s,{'numeric'},{'scalar','positive','finite'});
validateattributes(CFG.channelUpdateStep_s,{'numeric'},{'scalar','positive','finite'});
assert(mod(CFG.duration_s,CFG.channelUpdateStep_s)==0, ...
    'GSL:TimeGrid','Duration must be an integer multiple of the sample step.');
validateattributes(CFG.minElevation_deg,{'numeric'},{'scalar','>=',0,'<=',90});
sc = satelliteScenario(CFG.startTime,CFG.startTime+seconds(CFG.duration_s), ...
    CFG.channelUpdateStep_s);
sats = createConstellation(sc,CFG);
gs = groundStation(sc,CFG.gsLatitude_deg,CFG.gsLongitude_deg, ...
    'Altitude',CFG.gsAltitude_m,'Name',CFG.gsName, ...
    'MinElevationAngle',CFG.minElevation_deg);
links = access(gs,sats); % only geometric access, not RF link closure
fprintf('===== Ground Station =====\nLatitude  : %.4f deg\nLongitude : %.4f deg\nAltitude  : %g m (WGS84)\n==========================\n', ...
    CFG.gsLatitude_deg,CFG.gsLongitude_deg,CFG.gsAltitude_m);
G = computeGeometry(sc,sats,gs,links,CFG);
R = struct('config',CFG,'scenario',sc,'satellites',sats, ...
    'groundStation',gs,'access',links,'geometry',G,'viewer',[]);
if CFG.exportResults
    if ~isfolder(CFG.outputDir), mkdir(CFG.outputDir); end
    save(fullfile(CFG.outputDir,'geometry_stage1.mat'),'CFG','G','-v7');
    summary = table(G.time_s,G.visibleCount,G.hasCandidate,G.maxElevation_deg, ...
        'VariableNames',{'time_s','visibleSatelliteCount','hasCandidate','maxElevation_deg'});
    [~,exampleIndex]=max(G.elevation_deg(1,:));
    summary.fixedSatelliteIndex=repmat(exampleIndex,height(summary),1);
    summary.fixedSatelliteElevation_deg=G.elevation_deg(:,exampleIndex);
    writetable(summary,fullfile(CFG.outputDir,'visibility_summary.csv'));
    satellites = table(G.satelliteIndex,G.satelliteName, ...
        'VariableNames',{'satelliteIndex','satelliteName'});
    writetable(satellites,fullfile(CFG.outputDir,'satellite_index.csv'));
end
[L,D] = computeLinkState(G,sats,CFG);
R.linkState=L;
if CFG.debug
    R.servingDebug=D;
    disp(D(D.time_s>=470 & D.time_s<=492,:));
    if CFG.exportResults, writetable(D,fullfile(CFG.outputDir,'serving_debug.csv')); end
end
if isfield(CFG,'enablePackets') && CFG.enablePackets
    P = simulatePacketTransmission(L,CFG);
    M = computePacketMetrics(P,CFG.rollingWindow_s);
    R.linkState = L; R.packetTable = P; R.packetMetrics = M;
    width=max(0,min(L.time_s(2:end),CFG.duration_s)-L.time_s(1:end-1));
    M.totalOutageDuration_s=sum(width.*double(~L.isLinkAvailable(1:end-1)));
    R.packetMetrics=M;
    reportPacketResults(L,P,M,CFG);
else
    if CFG.makePlots, plotResults(L,[],[],CFG); end
end
if CFG.openViewer
    R.viewerController = GSLViewerController(sc,sats,gs,links,L,CFG);
    R.viewer = R.viewerController.Viewer;
    if CFG.makePlots, attachGSLPlaybackControls(R); end
end
end
