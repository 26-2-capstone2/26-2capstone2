function sats=createConstellation(sc,CFG)
% Exact requested count. Moving-grid ephemerides preserve relative geometry.
if isfield(CFG,'constellationType') && strcmp(CFG.constellationType,'moving_grid')
    [positionTT,velocityTT]=movingGSLGridEphemeris(CFG);
    sats=satellite(sc,positionTT,velocityTT,'CoordinateFrame','ecef');
    return;
end
validateattributes(CFG.numPlanes,{'numeric'},{'scalar','integer','positive','finite'});
validateattributes(CFG.satsPerPlane,{'numeric'},{'scalar','integer','positive','finite'});
validateattributes(CFG.phaseFactor,{'numeric'},{'scalar','integer','nonnegative','finite'});
validateattributes(CFG.satAltitude_m,{'numeric'},{'scalar','positive','finite'});
count=CFG.numPlanes*CFG.satsPerPlane;
if isfield(CFG,'totalSatellites') && ~isempty(CFG.totalSatellites)
    validateattributes(CFG.totalSatellites,{'numeric'},{'scalar','integer','positive','finite'});
    count=CFG.totalSatellites;
end
planes=min(CFG.numPlanes,count);
phase=mod(CFG.phaseFactor,planes);
type='walker_delta';
if isfield(CFG,'constellationType'), type=CFG.constellationType; end
assert(ismember(string(type),["iridium","walker_delta"]),'GSL:ConstellationType');
radius=CFG.earthEquatorialRadius_m+CFG.satAltitude_m;
spacing=360/planes;
name='StarlinkLike';
if strcmp(type,'iridium')
    validateattributes(CFG.orbitReferenceRadius_m,{'numeric'},{'scalar','positive','finite'});
    radius=CFG.orbitReferenceRadius_m+CFG.satAltitude_m;
    spacing=180/planes;
    if planes==6
        spacing=CFG.iridiumPlaneSpacing_deg;
    end
    name='IridiumLike';
end
if strcmp(type,'walker_delta') && mod(count,planes)==0
    sats=walkerDelta(sc,radius,CFG.inclination_deg,count,planes,phase, ...
        'RAAN',CFG.raan0_deg,'ArgumentOfLatitude',CFG.argumentOfLatitude0_deg, ...
        'OrbitPropagator','two-body-keplerian','Name','StarlinkLike');
    return;
end
% Explicit elements support Iridium spacing and plane populations differing by one.
populations=repmat(floor(count/planes),1,planes);
populations(1:mod(count,planes))=populations(1:mod(count,planes))+1;
raan=zeros(1,count);
anomaly=zeros(1,count);
first=1;
for plane=1:planes
    n=populations(plane);
    rows=first:first+n-1;
    raan(rows)=CFG.raan0_deg+spacing*(plane-1);
    anomaly(rows)=CFG.argumentOfLatitude0_deg+(0:n-1)*360/n ...
        +360*phase*(plane-1)/count;
    first=first+n;
end
sats=satellite(sc,repmat(radius,1,count),zeros(1,count), ...
    repmat(CFG.inclination_deg,1,count),mod(raan,360),zeros(1,count), ...
    mod(anomaly,360),'OrbitPropagator','two-body-keplerian','Name',name);
end
