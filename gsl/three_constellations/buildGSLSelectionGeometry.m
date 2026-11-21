function G=buildGSLSelectionGeometry(C)
% Exact ephemerides used by existing moving-grid code, vectorized ENU AER.
% No new orbit model. Tested against Aerospace Toolbox aer/accessStatus.
[T,~]=movingGSLGridEphemeris(C);
times=seconds(T.Time-C.startTime); n=width(T); nt=height(T);
lat=deg2rad(C.gsLatitude_deg); lon=deg2rad(C.gsLongitude_deg);
e2=(1/298.257223563)*(2-1/298.257223563);
N=C.earthEquatorialRadius_m/sqrt(1-e2*sin(lat)^2); h=C.gsAltitude_m;
origin=[(N+h)*cos(lat)*cos(lon),(N+h)*cos(lat)*sin(lon),(N*(1-e2)+h)*sin(lat)];
up=[cos(lat)*cos(lon);cos(lat)*sin(lon);sin(lat)];
east=[-sin(lon);cos(lon);0]; north=[-sin(lat)*cos(lon);-sin(lat)*sin(lon);cos(lat)];
el=zeros(nt,n); range=el; first=zeros(3,n); last=first;
for id=1:n
    xyz=T{:,id}; los=xyz-origin;
    range(:,id)=sqrt(sum(los.^2,2));
    el(:,id)=atan2d(los*up,hypot(los*east,los*north));
    first(:,id)=xyz(1,:).'; last(:,id)=xyz(end,:).';
end
[p,s]=gslSatelliteGrid(C);
G=struct('time_s',times,'elevation_deg',el,'slantRange_m',range, ...
    'isVisible',el>=C.minElevation_deg,'planeIndex',p,'satelliteInPlane',s, ...
    'positionStartECEF_m',first,'positionEndECEF_m',last);
G.visibleCount=sum(G.isVisible,2);
end
