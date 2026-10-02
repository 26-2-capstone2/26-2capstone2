function R = main_gsl_simulation(CFG)
% Run: R = main_gsl_simulation; then play(R.scenario).
% Stage 1: orbit, GS, elevation, visibility and visualization only.
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
fprintf('Stage 1: %d satellites, %.0f s, %.1f s sample interval.\n', ...
    numel(sats),CFG.duration_s,CFG.channelUpdateStep_s);
G = computeGeometry(sc,sats,gs,links,CFG);
R = struct('config',CFG,'scenario',sc,'satellites',sats, ...
    'groundStation',gs,'access',links,'geometry',G,'viewer',[]);
if CFG.exportResults
    if ~isfolder(CFG.outputDir), mkdir(CFG.outputDir); end
    save(fullfile(CFG.outputDir,'geometry_stage1.mat'),'CFG','G','-v7');
    summary = table(G.time_s,G.visibleCount,G.hasCandidate,G.maxElevation_deg, ...
        'VariableNames',{'time_s','visibleSatelliteCount','hasCandidate','maxElevation_deg'});
    writetable(summary,fullfile(CFG.outputDir,'visibility_summary.csv'));
    satellites = table(G.satelliteIndex,G.satelliteName, ...
        'VariableNames',{'satelliteIndex','satelliteName'});
    writetable(satellites,fullfile(CFG.outputDir,'satellite_index.csv'));
end
if CFG.makePlots, plotResults(G,CFG); end
if CFG.openViewer
    % All satellites participate in analysis and are shown as simple markers.
    % Access lines are visible only while geometric access exists.
    R.viewer = satelliteScenarioViewer(sc,'ShowDetails',false);
    show(gs); show(links);
end
fprintf('Visible satellites min/max: %d / %d. Candidate availability: %.2f%% of samples.\n', ...
    min(G.visibleCount),max(G.visibleCount),100*mean(G.hasCandidate));
fprintf('Use play(R.scenario) in the MATLAB desktop to animate.\n');
end
