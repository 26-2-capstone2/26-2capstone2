function saveGSLAttenuation(f)
assert(getappdata(f,'GSLSelectedWeather')=="manual", ...
    'GSL:SelectManual','Apply the attenuation slider before saving.');
B=getappdata(f,'GSLWeatherCases'); Q=B.manual; C=Q.config;
C.outputDir=fullfile(fileparts(mfilename('fullpath')),'results_attenuation', ...
    sprintf('loss_%.1f_dB',C.environmentLoss_dB));
C.exportResults=true; C.makePlots=false;
reportPacketResults(Q.linkState,Q.packetTable,Q.packetMetrics,C);
exportapp(f,fullfile(C.outputDir,'attenuation_performance.png'));
diag=findall(groot,'Name','GSL Uplink - Channel and Loss Runs');
if numel(diag)==1, exportgraphics(diag,fullfile(C.outputDir,'uplink_channel_loss_runs.png'),'Resolution',140); end
fid=fopen(fullfile(C.outputDir,'MODEL_LIMITS.txt'),'w','n','UTF-8'); assert(fid>=0);
guard=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,['Slider is total environment loss; no atmospheric components are added again.\n' ...
    'Not an observed weather classification. Fixed bandwidth/rate; no ACM, queue or retries.\n' ...
    'Outside support uses named research approximations; NOT full-range validated decoder performance.\n' ...
    'High Eb/N0 policy: %s; low Eb/N0 policy: %s. See packet phyStatus for provenance.\n'],C.highSNRPolicy,C.lowSNRPolicy);
fprintf('Saved manual attenuation experiment: %s\n',C.outputDir);
end
