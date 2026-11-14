function R=main_gsl_link_interface(policy,CFG)
% Stable-ID policy integration. F5 runs a highest-SNR EXAMPLE, without training.
% policy(observation, fullSatelliteTable) must return a visible satellite ID.
if nargin<2, CFG=configGSL(); end
if nargin<1 || isempty(policy)
    policy=@highestVisibleSNR;
    fprintf('Interface example: highest visible SNR. Supply a callback for DDQN.\n');
end
assert(isa(policy,'function_handle'),'GSL:IDPolicyCallback');
env=GSLRLEnvironment([],CFG);
env.reset();
initial=env.allSatelliteStates();
disp(initial);
states=cell(CFG.duration_s,1);
decisions=cell(CFG.duration_s,1);
done=false; k=0;
while ~done
    k=k+1;
    observation=env.observe();
    allSatellites=env.allSatelliteStates();
    satelliteID=policy(observation,allSatellites);
    [~,feedback,done]=env.stepSatelliteID(satelliteID);
    states{k}=allSatellites;
    decisions{k}=rmfield(feedback,'rewardDetails');
end
[P,M]=env.results();
T=vertcat(states{:});
decisions=struct2table(vertcat(decisions{:}));
% Piecewise-constant links over the same one-second decisions.
packetRows=1:CFG.packetRate_pps:height(P);
id=decisions.servingSatID;
L=table([decisions.startTime_s;CFG.duration_s],[id;id(end)], ...
    [id>0;id(end)>0],[decisions.handover;false], ...
    [P.snr_dB(packetRows);P.snr_dB(end)], ...
    [P.servingElevation_deg(packetRows);P.servingElevation_deg(end)], ...
    [P.propagation_delay_ms(packetRows);P.propagation_delay_ms(end)], ...
    'VariableNames',{'time_s','servingSatID','isLinkAvailable','handoverEvent', ...
    'snr_dB','elevation_deg','propagationDelay_ms'});
reportCFG=CFG;
reportCFG.makePlots=false;
reportCFG.environmentLoss_dB=env.environmentLoss_dB;
reportCFG.outputDir=fullfile(CFG.outputDir,'id_policy_interface');
if CFG.exportResults
    if ~isfolder(reportCFG.outputDir), mkdir(reportCFG.outputDir); end
    writetable(T,fullfile(reportCFG.outputDir,'all_satellite_states.csv'));
    writetable(decisions,fullfile(reportCFG.outputDir,'id_policy_decisions.csv'));
end
reportPacketResults(L,P,M,reportCFG);
R=struct('config',CFG,'initialSatelliteStates',initial,'satelliteStates',T, ...
    'decisions',decisions,'packetTable',P,'packetMetrics',M, ...
    'outputDir',reportCFG.outputDir,'policy',func2str(policy));
end

function satelliteID=highestVisibleSNR(~,allSatellites)
T=allSatellites(allSatellites.isVisible,:);
satelliteID=0;
if isempty(T), return; end
T=sortrows(T,{'snr_dB','satelliteID'},{'descend','ascend'});
satelliteID=T.satelliteID(1);
end
