function CFG = configGSL()
% CONFIG: Stage 1 geometry only. All distances are SI unless stated.
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
CFG.openViewer = true;
CFG.makePlots = true;
CFG.exportResults = true;
CFG.outputDir = fullfile(fileparts(mfilename('fullpath')),'results_stage1');
end
