function [G,sc,sats,gs,links] = buildGSLGeometry(CFG)
% Build the common GSL scenario and sample its satellite geometry.
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
G = computeGeometry(sc,sats,gs,links,CFG);
end
