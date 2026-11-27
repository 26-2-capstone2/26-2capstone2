function R=gslStaticFrontMain(mode,seed)
% No argument: reopen saved results. 'run',seed: generate a new episode.
if nargin<1,mode='show';end
C=configGSLStaticFront();if nargin<2,seed=C.staticDefaultEpisodeSeed;end
folder=fullfile(C.outputDir,sprintf('seed_%d',seed));
if strcmpi(mode,'show')&&isfile(fullfile(C.outputDir,'latest_result.txt'))&&nargin<2
    folder=fullfile(C.outputDir,strtrim(fileread(fullfile(C.outputDir,'latest_result.txt'))));
end
if strcmpi(mode,'run')||~isfile(fullfile(folder,'result.mat'))
    R=run_gsl_static_front(seed,C);
else
    D=load(fullfile(folder,'result.mat'),'R');R=D.R;R.outputDir=folder;R.config.outputDir=folder;
    fprintf('Reopened saved static environment results: %s\n',folder);
end
showGSLStaticFront(R,C.openPacketViewer);
disp(R.initialCandidates(:,{'satelliteID','row','column','snr_dB','elevation_deg','PER'}));
end
