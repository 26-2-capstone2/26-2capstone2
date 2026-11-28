function R=main_gsl_static_36x36(mode)
if nargin<1,mode='show';end
addpath(fullfile(fileparts(mfilename('fullpath')),'static_reward_1128'));
R=gslStaticSizeMain(mode,36,36);
end
