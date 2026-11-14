function [selectedID,blocked]=applyGSLHysteresis(proposedID,T,margin_dB)
% Evaluation gate: zero disables it; positive margins require SNR improvement.
validateattributes(margin_dB,{'numeric'},{'scalar','finite','nonnegative'});
selectedID=proposedID; blocked=false;
if isempty(T)
    assert(proposedID==0,'GSL:HysteresisInvisibleID'); return;
end
target=find(T.satelliteID==proposedID,1);
assert(~isempty(target),'GSL:HysteresisInvisibleID');
old=find(T.isServing,1);
if margin_dB==0 || isempty(old) || T.satelliteID(old)==proposedID, return; end
if T.snr_dB(target)<T.snr_dB(old)+margin_dB
    selectedID=T.satelliteID(old); blocked=true;
end
end
