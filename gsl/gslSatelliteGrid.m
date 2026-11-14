function [planeIndex,satelliteInPlane]=gslSatelliteGrid(CFG,count)
% Zero-based ISL coordinates in plane-major satellite-ID order.
if nargin<2
    count=CFG.numPlanes*CFG.satsPerPlane;
    if isfield(CFG,'totalSatellites') && ~isempty(CFG.totalSatellites)
        count=CFG.totalSatellites;
    end
end
planes=min(CFG.numPlanes,count);
populations=repmat(floor(count/planes),1,planes);
populations(1:mod(count,planes))=populations(1:mod(count,planes))+1;
planeIndex=zeros(count,1);
satelliteInPlane=zeros(count,1);
first=1;
for plane=1:planes
    n=populations(plane);
    rows=first:first+n-1;
    planeIndex(rows)=plane-1;
    satelliteInPlane(rows)=(0:n-1).';
    first=first+n;
end
end
