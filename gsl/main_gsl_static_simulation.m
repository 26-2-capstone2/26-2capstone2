function R=main_gsl_static_simulation(varargin)
here=fileparts(mfilename('fullpath'));
module=fullfile(here,'static_front_1127');
if isfolder(module),addpath(module);else,addpath(here);end
R=gslStaticFrontMain(varargin{:});
end
