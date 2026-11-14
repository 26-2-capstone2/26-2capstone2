function exportGSLGridInterface(G,sats,C)
% Export a shared coordinate/ID contract for ISL integration.
assert(strcmp(C.constellationType,'moving_grid'));
[p,v]=states(sats,'CoordinateFrame','ecef');
count=numel(sats); n=numel(G.time_s);
assert(size(p,1)==3 && size(p,2)==n && size(p,3)==count,'GSL:SharedStatesShape');
position=reshape(permute(p,[2 3 1]),[],3);
velocity=reshape(permute(v,[2 3 1]),[],3);
satelliteID=repelem((1:count).',n);
T=table(repmat(G.time_s,count,1),satelliteID,G.planeIndex(satelliteID), ...
    G.satelliteInPlane(satelliteID),position(:,1),position(:,2),position(:,3), ...
    velocity(:,1),velocity(:,2),velocity(:,3),G.elevation_deg(:),G.isVisible(:), ...
    'VariableNames',{'time_s','satelliteID','p','s','x_ecef_m','y_ecef_m', ...
    'z_ecef_m','vx_ecef_mps','vy_ecef_mps','vz_ecef_mps','elevation_deg','visible'});
T=sortrows(T,{'time_s','satelliteID'});
writetable(T,fullfile(C.outputDir,'shared_grid_positions.csv'));
stepP=[0 0 -1 1]; stepS=[-1 1 0 0]; delays=[.007 .007 .002 .002];
links=zeros(4*count,10); k=0;
for plane=0:C.numPlanes-1
    for satellite=0:C.satsPerPlane-1
        from=plane*C.satsPerPlane+satellite+1;
        for d=1:4
            toP=plane+stepP(d); toS=satellite+stepS(d);
            if toP<0 || toP>=C.numPlanes || toS<0 || toS>=C.satsPerPlane
                continue;
            end
            to=toP*C.satsPerPlane+toS+1;
            distance=norm(G.positionStartECEF_m(:,from)-G.positionStartECEF_m(:,to));
            linkID=plane+C.numPlanes*satellite+C.numPlanes*C.satsPerPlane*(d-1);
            k=k+1;
            links(k,:)=[linkID,plane,satellite,d,toP,toS,from,to,distance,delays(d)];
        end
    end
end
L=array2table(links(1:k,:),'VariableNames',{'islLinkID','fromP','fromS','direction', ...
    'toP','toS','fromSatelliteID','toSatelliteID','distance_m','islAbstractDelay_s'});
L.propagationDelay_s=L.distance_m/299792458;
L=sortrows(L,'islLinkID');
writetable(L,fullfile(C.outputDir,'shared_grid_links.csv'));
passTime=C.gridPassTime_s;
if isempty(passTime), passTime=C.duration_s/2; end
metadata=struct('model','experimental_rigid_moving_grid', ...
    'islTopology',sprintf('grid:%dx%d',C.numPlanes,C.satsPerPlane), ...
    'numPlanes',C.numPlanes,'satsPerPlane',C.satsPerPlane,'wrapP',false,'wrapS',false, ...
    'coordinateFrame','ECEF','lengthUnit','m','timeUnit','s', ...
    'satelliteIDFormula','p*satsPerPlane+s+1', ...
    'islLinkIDFormula','p+numPlanes*s+numPlanes*satsPerPlane*(direction-1)', ...
    'crossSpacing_m',C.gridCrossSpacing_m,'alongSpacing_m',C.gridAlongSpacing_m, ...
    'centerSpeed_mps',C.gridCenterSpeed_mps,'heading_deg',C.gridHeading_deg, ...
    'centerPassTime_s',passTime,'radius_m',C.orbitReferenceRadius_m+C.satAltitude_m, ...
    'assumptions','Spacing and motion are new research assumptions. ISL 7/2 ms are abstract delays, separate from exported propagation delays.');
fid=fopen(fullfile(C.outputDir,'shared_grid_contract.json'),'w','n','UTF-8'); assert(fid>=0);
cleanup=onCleanup(@()fclose(fid));
fprintf(fid,'%s',jsonencode(metadata,'PrettyPrint',true));
end
