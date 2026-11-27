function setupStaticReward()
here=fileparts(mfilename('fullpath'));base=fileparts(here);
if ~isfolder(fullfile(base,'static_front_1127'))
    base='C:/Users/succe/Desktop/codex/1125/GSL_research_1126/gsl';
end
addpath(here,base,fullfile(base,'static_front_1127'),fullfile(base,'ddqn_6x11'),fullfile(base,'three_constellations'));
end
