function G=buildGSLStaticFrontGeometry(C,episodeSeed)
% One random rigid placement per episode, fixed in ECEF for the full episode.
assert(strcmp(C.constellationType,'static_front_grid'));
validateattributes(C.numPlanes,{'numeric'},{'scalar','integer','positive'});
validateattributes(C.satsPerPlane,{'numeric'},{'scalar','integer','>=',2});
assert(C.gridCrossSpacing_m>0&&C.gridAlongSpacing_m>0&&C.channelUpdateStep_s==1);
radius=C.orbitReferenceRadius_m+C.satAltitude_m;
assert((C.numPlanes-1)*C.gridCrossSpacing_m/radius<pi&&(C.satsPerPlane-1)*C.gridAlongSpacing_m/radius<pi);
seed=mod(C.staticLayoutSeed+episodeSeed,2^32);stream=RandStream('mt19937ar','Seed',seed);
u=rand(stream,3,1);heading=C.staticHeadingRange_deg(1)+diff(C.staticHeadingRange_deg)*u(1);
crossOffset=C.gridCrossSpacing_m*(C.staticCrossOffsetFraction(1)+diff(C.staticCrossOffsetFraction)*u(2));
alongOffset=C.gridAlongSpacing_m*(C.staticAlongOffsetFraction(1)+diff(C.staticAlongOffsetFraction)*u(3));
lat=deg2rad(C.gsLatitude_deg);lon=deg2rad(C.gsLongitude_deg);e2=(1/298.257223563)*(2-1/298.257223563);
N=C.earthEquatorialRadius_m/sqrt(1-e2*sin(lat)^2);h=C.gsAltitude_m;
origin=[(N+h)*cos(lat)*cos(lon);(N+h)*cos(lat)*sin(lon);(N*(1-e2)+h)*sin(lat)];
radial=origin/norm(origin);east=[-sin(lon);cos(lon);0];north=cross(radial,east);north=north/norm(north);
along=cosd(heading)*north+sind(heading)*east;across=cross(radial,along);across=across/norm(across);
geodeticUp=[cos(lat)*cos(lon);cos(lat)*sin(lon);sin(lat)];
geodeticNorth=[-sin(lat)*cos(lon);-sin(lat)*sin(lon);cos(lat)];
[p,s]=gslSatelliteGrid(C);crossArc=(p-(C.numPlanes-1)/2)*C.gridCrossSpacing_m+crossOffset;
alongArc=s*C.gridAlongSpacing_m+alongOffset;
beta=crossArc/radius;theta=alongArc/radius;
xyz=radius*((cos(beta).*cos(theta))*radial.'+(cos(beta).*sin(theta))*along.'+sin(beta)*across.');
los=xyz-origin.';range=sqrt(sum(los.^2,2));el=atan2d(los*geodeticUp,hypot(los*east,los*geodeticNorth));
az=mod(atan2d(los*east,los*geodeticNorth),360);
times=(0:C.channelUpdateStep_s:C.duration_s).';nt=numel(times);
G=struct('time_s',times,'elevation_deg',repmat(el.',nt,1),'slantRange_m',repmat(range.',nt,1), ...
    'isVisible',repmat((el>=C.minElevation_deg).',nt,1),'planeIndex',p,'satelliteInPlane',s, ...
    'positionStartECEF_m',xyz.','positionEndECEF_m',xyz.','velocityECEF_mps',zeros(3,numel(p)), ...
    'azimuth_deg',repmat(az.',nt,1));
G.visibleCount=sum(G.isVisible,2);
G.staticSatellites=table((1:numel(p)).',p,s,p+1,s+1,crossArc/1000,alongArc/1000, ...
    xyz(:,1),xyz(:,2),xyz(:,3),range/1000,el,az,el>=C.minElevation_deg, ...
    'VariableNames',{'satelliteID','p_zero_based','s_zero_based','row','column','crossCoordinate_km','alongCoordinate_km', ...
    'x_ecef_m','y_ecef_m','z_ecef_m','slantRange_km','elevation_deg','azimuth_deg','visible'});
G.layout=struct('model','static_front_grid','episodeSeed',episodeSeed,'layoutSeed',seed,'heading_deg',heading, ...
    'crossOffset_m',crossOffset,'alongOffset_m',alongOffset,'frontColumn',1,'centerAlongCoordinate_m',mean(alongArc), ...
    'gsAlongCoordinate_m',0,'gsCrossCoordinate_m',0,'positionsFixed',true,'anglesDerivedFromCoordinates',true);
assert(all(G.visibleCount>0),'STATIC:NoCandidate');
end
