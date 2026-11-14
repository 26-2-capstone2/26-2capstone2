function [positionTT,velocityTT]=movingGSLGridEphemeris(C)
% Kinematic spherical grid, rigidly rotating in ECEF. Research assumptions.
validateattributes(C.gridCrossSpacing_m,{'numeric'},{'scalar','positive','finite'});
validateattributes(C.gridAlongSpacing_m,{'numeric'},{'scalar','positive','finite'});
validateattributes(C.gridCenterSpeed_mps,{'numeric'},{'scalar','positive','finite'});
validateattributes(C.gridHeading_deg,{'numeric'},{'scalar','finite'});
passTime=C.gridPassTime_s;
if isempty(passTime), passTime=C.duration_s/2; end
validateattributes(passTime,{'numeric'},{'scalar','finite','>=',0,'<=',C.duration_s});
validateattributes(C.numPlanes,{'numeric'},{'scalar','integer','positive'});
validateattributes(C.satsPerPlane,{'numeric'},{'scalar','integer','positive'});
count=C.numPlanes*C.satsPerPlane;
assert(~isfield(C,'totalSatellites') || isempty(C.totalSatellites), ...
    'GSL:GridDimensions','Use numPlanes and satsPerPlane for the moving grid.');
t=(0:C.channelUpdateStep_s:C.duration_s).';
radius=C.orbitReferenceRadius_m+C.satAltitude_m;
assert((C.numPlanes-1)*C.gridCrossSpacing_m/radius<pi && ...
    (C.satsPerPlane-1)*C.gridAlongSpacing_m/radius<pi, ...
    'GSL:GridExtent','Grid must span less than 180 degrees on each axis.');
lat=deg2rad(C.gsLatitude_deg); lon=deg2rad(C.gsLongitude_deg);
f=1/298.257223563; e2=f*(2-f);
N=C.earthEquatorialRadius_m/sqrt(1-e2*sin(lat)^2);
gs=[(N+C.gsAltitude_m)*cos(lat)*cos(lon); ...
    (N+C.gsAltitude_m)*cos(lat)*sin(lon); (N*(1-e2)+C.gsAltitude_m)*sin(lat)];
up=gs/norm(gs);
east=[-sin(lon);cos(lon);0];
north=cross(up,east); north=north/norm(north);
along=cosd(C.gridHeading_deg)*north+sind(C.gridHeading_deg)*east;
across=cross(up,along); across=across/norm(across);
omega=C.gridCenterSpeed_mps/radius;
positionTT=timetable('RowTimes',C.startTime+seconds(t));
velocityTT=timetable('RowTimes',C.startTime+seconds(t));
for p=0:C.numPlanes-1
    beta=(p-(C.numPlanes-1)/2)*C.gridCrossSpacing_m/radius;
    for s=0:C.satsPerPlane-1
        theta=omega*(t-passTime)+(s-(C.satsPerPlane-1)/2)*C.gridAlongSpacing_m/radius;
        position=radius*(cos(beta)*(cos(theta)*up.'+sin(theta)*along.') ...
            +sin(beta)*repmat(across.',numel(t),1));
        velocity=radius*omega*cos(beta)*(-sin(theta)*up.'+cos(theta)*along.');
        name=sprintf('Grid_p%d_s%d',p,s);
        positionTT.(name)=position;
        velocityTT.(name)=velocity;
    end
end
assert(width(positionTT)==count);
end
