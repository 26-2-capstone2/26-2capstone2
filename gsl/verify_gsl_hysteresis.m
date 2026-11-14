function verify_gsl_hysteresis()
T=table([11;22],[1;1.05],[true;false],'VariableNames',{'satelliteID','snr_dB','isServing'});
[id,b]=applyGSLHysteresis(22,T,0); assert(id==22 && ~b);
[id,b]=applyGSLHysteresis(22,T,.1); assert(id==11 && b);
T.snr_dB(2)=1.1; [id,b]=applyGSLHysteresis(22,T,.1); assert(id==22 && ~b);
T.snr_dB(2)=1.4; [id,b]=applyGSLHysteresis(22,T,.3); assert(id==22 && ~b);
[id,b]=applyGSLHysteresis(22,T,.5); assert(id==11 && b);
T.isServing(:)=false; [id,b]=applyGSLHysteresis(22,T,.5); assert(id==22 && ~b);
[id,b]=applyGSLHysteresis(0,T([],:),.5); assert(id==0 && ~b);
fprintf('PASS hysteresis gate off, threshold, margins, invisible old link, outage.\n');
end
