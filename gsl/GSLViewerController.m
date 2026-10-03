classdef GSLViewerController < GSLManualViewerController
    % Compatibility name; main uses the new manual controller directly.
    methods
        function obj=GSLViewerController(varargin)
            obj@GSLManualViewerController(varargin{:});
        end
    end
end
