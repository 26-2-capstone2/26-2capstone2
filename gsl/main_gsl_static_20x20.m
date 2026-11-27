function R=main_gsl_static_20x20(mode)
if nargin<1,mode='show';end
addpath(fullfile(fileparts(mfilename('fullpath')),'static_reward_1128'));
R=gslStaticSizeMain(mode,20,20);
end
