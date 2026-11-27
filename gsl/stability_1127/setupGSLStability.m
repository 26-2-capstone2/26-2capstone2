function gsl=setupGSLStability()
here=fileparts(mfilename('fullpath'));gsl=fileparts(here);
if ~isfolder(fullfile(gsl,'three_constellations')),gsl='C:/Users/succe/Desktop/codex/1125/GSL_research_1126/gsl';end
addpath(gsl,fullfile(gsl,'three_constellations'),fullfile(gsl,'ddqn_6x11'),here);
end
