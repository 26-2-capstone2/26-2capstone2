function R=open_saved_gsl_nstep_model(n)
if nargin<1,n=1;end
assert(ismember(n,[1 3 5]));setupGSLNStep();here=fileparts(mfilename('fullpath'));
base=fullfile(here,sprintf('results_n%d',n));out=fullfile(base,strtrim(fileread(fullfile(base,'latest_result.txt'))));
S=load(fullfile(out,'study.mat'),'R');R=S.R;R.outputDir=out;R.viewer=GSLTrendResultViewer(R);
end
