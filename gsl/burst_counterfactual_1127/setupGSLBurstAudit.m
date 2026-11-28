function source=setupGSLBurstAudit()
here=fileparts(mfilename('fullpath'));source=fullfile(fileparts(here),'gsl-nstep-1127');
if ~isfolder(source),source=fullfile(fileparts(here),'nstep_1127');end
if ~isfolder(source),source='C:/Users/succe/Desktop/codex/1125/GSL_research_1126/gsl/nstep_1127';end
addpath(source,here);setupGSLNStep();
end
