function [geometries,configs]=prepareGSLThreeGeometries(O)
if ~isfolder(O.cacheDir),mkdir(O.cacheDir);end
geometries=cell(3,1); configs=cell(3,1);
for k=1:3
    C=O.baseConfig; C.numPlanes=O.sizes(k,1); C.satsPerPlane=O.sizes(k,2);
    C.initialEnvironmentLoss_dB=O.environmentLoss_dB;
    C.makePlots=false; C.openPacketViewer=false; C.exportResults=false;
    path=fullfile(O.cacheDir,sprintf('grid_%dx%d.mat',C.numPlanes,C.satsPerPlane));
    use=false;
    if isfile(path)
        S=load(path,'G','config'); old=S.config; current=C;
        % File location and plotting/export switches do not change geometry.
        fields={'numPlanes','satsPerPlane','duration_s','channelUpdateStep_s', ...
            'startTime','gsLatitude_deg','gsLongitude_deg','gsAltitude_m', ...
            'earthEquatorialRadius_m','orbitReferenceRadius_m','satAltitude_m', ...
            'gridCrossSpacing_m','gridAlongSpacing_m','gridCenterSpeed_mps', ...
            'gridHeading_deg','gridPassTime_s','minElevation_deg'};
        use=all(cellfun(@(f)isequaln(old.(f),current.(f)),fields));
    end
    if use, G=S.G; else
        G=buildGSLSelectionGeometry(C); config=C; %#ok<NASGU>
        save(path,'G','config','-v7');
    end
    C.candidateCapacity=max(G.visibleCount); % no hidden top-13 truncation
    geometries{k}=G; configs{k}=C;
    fprintf('Geometry %dx%d: %d satellites; visible %d..%d; radius filter OFF\n', ...
        C.numPlanes,C.satsPerPlane,C.numPlanes*C.satsPerPlane,min(G.visibleCount),max(G.visibleCount));
end
end
