function saveGSLAttenuation(f)
assert(getappdata(f,'GSLSelectedWeather')=="manual", ...
    'GSL:SelectManual','Apply the attenuation slider before saving.');
B=getappdata(f,'GSLWeatherCases'); Q=B.manual; C=Q.config;
C.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_attenuation', ...
    sprintf('extra_%.1f_dB',C.manualExtraLoss_dB));
C.exportResults=true; C.makePlots=false;
reportPacketResults(Q.linkState,Q.packetTable,Q.packetMetrics,C);
exportapp(f,fullfile(C.outputDir,'attenuation_performance.png'));
fid=fopen(fullfile(C.outputDir,'MODEL_LIMITS.txt'),'w','n','UTF-8'); assert(fid>=0);
guard=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,['Manual additional loss on CLEAR GAS baseline; clouds/rain profiles are not added.\n' ...
    'Not an observed weather classification. Fixed bandwidth/rate; no ACM, queue or retries.\n' ...
    'Outside published Eb/N0 support is UNRESOLVED, not loss or success.\n' ...
    'NaN overall metrics = incomplete PHY evaluation. Known loss runs are partial when unresolved > 0.\n']);
fprintf('Saved manual attenuation experiment: %s\n',C.outputDir);
end
