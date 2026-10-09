function [E, S, T] = run_gsl_isl_bridge(R)
% GSL single-station trace -> logical ISL 6x6 bridge (NOT physical E2E)
% Input R = main_gsl_simulation() result. 100ms is the project E2E deadline.
if nargin < 1
    error('First run R = main_gsl_simulation(); then run_gsl_isl_bridge(R)');
end
P = R.packetTable;
needed = {'packetID','time_s','received','propagation_delay_ms','transmission_delay_ms'};
assert(all(ismember(needed,P.Properties.VariableNames)), 'GSL packet fields missing');
assert(all(isfinite(P.time_s)), 'Invalid GSL packet creation time');
assert(all(P.packetID == (1:height(P))'), 'Unexpected packet IDs');
% GSL currently models one downlink. Use its success trace as a proxy for
% first GSL stage only; DO NOT interpret as modeled uplink or full E2E.
ok = logical(P.received);
assert(~any(isnan(P.propagation_delay_ms(ok)) | isnan(P.transmission_delay_ms(ok))), 'GSL delay unavailable');
entryTime = P.time_s(ok) + (P.propagation_delay_ms(ok) + P.transmission_delay_ms(ok))/1000;
E = table(P.packetID(ok), P.time_s(ok), entryTime, ...
    'VariableNames', {'packet_id','generation_time_s','isl_entry_time_s'});
E = sortrows(E, {'isl_entry_time_s','packet_id'});
root = fileparts(mfilename('fullpath'));
addpath(fullfile(root,'isl'));
C = config_isl();
% Keep the original simulation window; arrivals during last 3ms still enter.
C.simTime = max(C.simTime, ceil(max(E.isl_entry_time_s)/C.stepTime)+2);
S = run_isl_sim(C, C.genRate, 0, C.randomSeed, false, E);
% status 1 = on-time; 2 = late arrival; 4 = queue overflow; 5 = TTL loss
% status 0 = unfinished (also loss for this finite-run accounting)
N = height(P);
arrived = (S.status == 1 | S.status == 2);
late = S.status == 2;
loss = ~arrived;
T = struct();
T.generated = N;
T.gslPassed = height(E);
T.gslLost = N-height(E);
T.islArrived = nnz(arrived);
T.islLate = nnz(late);
T.islLost = nnz(loss);
T.logicalStageDelivered = nnz(arrived);
T.logicalStageLoss = T.gslLost + T.islLost;
T.deadlineDelivered = nnz(S.status == 1);
T.deadlineDeliveryRate = T.deadlineDelivered/N;
T.note = 'GSL single downlink trace used as stage proxy; logical ISL only. No uplink or destination downlink model.';
fprintf('\n===== GSL -> ISL LOGICAL BRIDGE (NOT E2E) =====\n');
fprintf('Generated: %d | GSL pass: %d | GSL loss: %d\n', N,T.gslPassed,T.gslLost);
fprintf('ISL arrived: %d | late: %d | ISL loss: %d\n',T.islArrived,T.islLate,T.islLost);
fprintf('Combined logical-stage loss: %d | 100ms on-time: %d (%.4f%% of original)\n', ...
    T.logicalStageLoss,T.deadlineDelivered,100*T.deadlineDeliveryRate);
fprintf('NOTE: This is NOT full User A to User B E2E.\n');
end
