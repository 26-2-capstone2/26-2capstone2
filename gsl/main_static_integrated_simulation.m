
function R = main_static_integrated_simulation(numPlanes, satsPerPlane, gslPolicy, seed)
% Static GSL - Python ISL integrated simulation
%
% Version 1.0
%
% Supported constellations:
%   6 x 11
%   20 x 20
%   36 x 36
%
% Current GSL policy: DDQN
% Current ISL mode: MOCK
%
% No DDQN retraining.
% Original GSL algorithms and checkpoints are preserved.

totalTimer = tic;

%% 1. Default arguments

if nargin < 1
    numPlanes = 6;
end

if nargin < 2
    satsPerPlane = 11;
end

if nargin < 3
    gslPolicy = 'DDQN';
end

if nargin < 4
    seed = 20282001;
end

validateattributes(numPlanes, ...
    {'numeric'}, {'scalar','integer','positive'});

validateattributes(satsPerPlane, ...
    {'numeric'}, {'scalar','integer','positive'});

validateattributes(seed, ...
    {'numeric'}, {'scalar','integer','positive'});

gslPolicy = upper(string(gslPolicy));

assert(isscalar(gslPolicy));

assert(gslPolicy == "DDQN", ...
    'Currently only DDQN is supported.');

totalSatellites = numPlanes * satsPerPlane;

fprintf('\n');
fprintf('========================================\n');
fprintf(' STATIC GSL - ISL INTEGRATION V1.0\n');
fprintf('========================================\n');

fprintf('Constellation: %d x %d\n', ...
    numPlanes, satsPerPlane);

fprintf('Total satellites: %d\n', totalSatellites);
fprintf('GSL policy: %s\n', gslPolicy);
fprintf('Evaluation seed: %d\n', seed);
fprintf('ISL mode: MOCK\n');

%% 2. Project paths

gslDir = fileparts(mfilename('fullpath'));

projectDir = fileparts(gslDir);

moduleDir = fullfile( ...
    gslDir, 'static_reward_1128');

integrationDir = fullfile( ...
    projectDir, 'gsl_isl_integration');

scriptFile = fullfile( ...
    integrationDir, 'mock_isl.py');

assert(isfolder(moduleDir));
assert(isfolder(integrationDir));
assert(isfile(scriptFile));

addpath(gslDir);
addpath(moduleDir);

setupStaticReward();

%% 3. Select trained checkpoint

fprintf('\n[STEP 1/10] Loading checkpoint...\n');

if numPlanes == 6 && satsPerPlane == 11

    modelDir = fullfile( ...
        moduleDir, ...
        'results_policy_comparison', ...
        '20261128_010145_246');

elseif numPlanes == 20 && satsPerPlane == 20

    modelDir = fullfile( ...
        moduleDir, ...
        'results_policy_20x20', ...
        '20261128_020831_235');

elseif numPlanes == 36 && satsPerPlane == 36

    modelDir = fullfile( ...
        moduleDir, ...
        'results_policy_36x36', ...
        '20261128_020843_233');

else

    error('Unsupported constellation size.');

end

modelFile = fullfile( ...
    modelDir, 'quadratic_agent_0100.mat');

runsFile = fullfile(modelDir, 'runs.csv');

assert(isfile(modelFile), ...
    'DDQN checkpoint file not found.');

assert(isfile(runsFile), ...
    'Original runs.csv not found.');

A = load(modelFile, 'checkpoint', 'O', 'D');

assert(isfield(A,'checkpoint'));
assert(isfield(A,'O'));
assert(isfield(A,'D'));

O = A.O;
D = A.D;

fprintf('Checkpoint: %s\n', modelFile);
fprintf('Checkpoint loading: PASS\n');

%% 4. Resolve local PHY curve

fprintf('\n[STEP 2/10] Validating configuration...\n');

originalCurveFile = O.baseConfig.phyToolboxCurveFile;

localCurveFile = fullfile( ...
    gslDir, ...
    'phy_toolbox', ...
    'ar4ja_qpsk_awgn_160B.csv');

assert(isfile(localCurveFile), ...
    'Local PHY curve file not found.');

O.baseConfig.phyToolboxCurveFile = localCurveFile;

T = readtable(localCurveFile);

requiredColumns = { ...
    'ebNo_dB', ...
    'PER', ...
    'CWER', ...
    'PER_lower95', ...
    'PER_upper95'};

assert(all(ismember( ...
    requiredColumns, ...
    T.Properties.VariableNames)));

assert(height(T) == 42);
assert(T.ebNo_dB(1) == -24);
assert(T.ebNo_dB(end) == 16);
assert(all(diff(T.ebNo_dB) > 0));
assert(all(isfinite(T.PER)));
assert(all(T.PER >= 0 & T.PER <= 1));

fprintf('PHY curve path correction: PASS\n');
fprintf('PHY curve validation: PASS\n');

%% 5. Validate saved experiment configuration

C = O.baseConfig;

assert(C.numPlanes == numPlanes);
assert(C.satsPerPlane == satsPerPlane);

assert(strcmp(C.constellationType, ...
    'static_front_grid'));

assert(strcmp(D.name, 'quadratic'));

assert(O.numEpisodes == 100);
assert(C.duration_s == 600);
assert(C.packetRate_pps == 60);
assert(C.packetSize_bytes == 160);

assert(abs(O.environmentLoss_dB - 6) < 1e-12);

assert(isempty(intersect( ...
    O.trainingSeeds, O.evaluationSeeds)));

assert(ismember(seed, O.evaluationSeeds), ...
    'Seed must belong to the saved evaluation seeds.');

assert(isscalar(O.evaluationQMargins));

margin = O.evaluationQMargins;

assert(abs(margin - 0.02) < 1e-12);

policyName = string(sprintf( ...
    '%s_Q%g', D.name, margin));

fprintf('Reward: %s\n', D.name);
fprintf('Q margin: %.4f\n', margin);
fprintf('Duration: %d s\n', C.duration_s);
fprintf('Packet rate: %d pps\n', C.packetRate_pps);
fprintf('Configuration validation: PASS\n');

%% 6. Restore frozen DDQN

fprintf('\n[STEP 3/10] Restoring DDQN...\n');

agent = GSLTrendDoubleDQN(O);

agent.restore(A.checkpoint);

updateCountBefore = agent.updateCount;

assert(updateCountBefore > 0);

assert(updateCountBefore == ...
    A.checkpoint.updateCount);

fprintf('Training updates: %d\n', updateCountBefore);
fprintf('DDQN restoration: PASS\n');

%% 7. Create static GSL environment

fprintf('\n[STEP 4/10] Creating static environment...\n');

env = createStaticRewardEpisode(O, seed, D);

G = env.geometry;

assert(numel(G.planeIndex) == totalSatellites);

assert(numel(G.satelliteInPlane) == ...
    totalSatellites);

assert(height(G.staticSatellites) == ...
    totalSatellites);

expectedID = ...
    G.planeIndex * satsPerPlane ...
    + G.satelliteInPlane + 1;

assert(isequal(expectedID(:), ...
    (1:totalSatellites).'));

assert(isequal( ...
    G.staticSatellites.satelliteID(:), ...
    expectedID(:)));

assert(all(G.planeIndex >= 0));
assert(all(G.planeIndex < numPlanes));

assert(all(G.satelliteInPlane >= 0));
assert(all(G.satelliteInPlane < satsPerPlane));

assert(G.layout.positionsFixed);
assert(all(G.visibleCount > 0));

fprintf('Visible satellites: %d\n', ...
    G.visibleCount(1));

fprintf('Static environment: PASS\n');
fprintf('Satellite ID mapping: PASS\n');

%% 8. Run frozen DDQN evaluation

fprintf('\n[STEP 5/10] Running GSL evaluation...\n');

gslTimer = tic;

while env.time < C.duration_s

    S = env.observe();

    assert(~isempty(S.ids));

    assert(size(S.features,1) == 11);

    q = agent.values(S);

    assert(numel(q) == numel(S.ids));
    assert(all(isfinite(q(:))));

    [~, j] = max(q);

    old = find(S.features(4,:) > 0, 1);

    if ~isempty(old) && q(j) < q(old) + margin

        j = old;

    end

    env.step(S.ids(j));

    if mod(env.time,100) == 0

        fprintf('GSL evaluation: %d / %d s\n', ...
            env.time, C.duration_s);

    end

end

gslEvaluationTime_s = toc(gslTimer);

updateCountAfter = agent.updateCount;

assert(updateCountBefore == updateCountAfter);

[P, M, L] = env.results();

assert(height(P) == M.generatedPackets);

assert(M.generatedPackets == ...
    C.duration_s * C.packetRate_pps);

assert(M.pendingPackets == 0);

assert(M.generatedPackets == ...
    M.receivedPackets + M.lostPackets);

assert(M.lostPackets == ...
    M.phyLossPackets ...
    + M.handoverLossPackets ...
    + M.outageLossPackets);

assert(M.handoverLossPackets == ...
    6 * sum(env.handovers));

fprintf('Frozen GSL evaluation: PASS\n');
fprintf('No training updates: PASS\n');
fprintf('GSL packet accounting: PASS\n');

%% 9. Compare original evaluation

fprintf('\n[STEP 6/10] Comparing original results...\n');

originalRuns = readtable(runsFile);

mask = ...
    string(originalRuns.policy) == policyName ...
    & originalRuns.seed == seed;

assert(sum(mask) == 1, ...
    'Matching original evaluation not found.');

reference = originalRuns(mask,:);

metric = [
    "Generated packets"
    "Received packets"
    "Lost packets"
    "Packet loss ratio (%)"
    "On-time delivery (%)"
    "Maximum consecutive loss"
    "Handovers"
    "PHY loss"
    "Handover loss"
    "Outage loss"
    "Pending packets"
];

original = [
    reference.generated
    reference.received
    reference.lost
    reference.loss_pct
    reference.onTime_pct
    reference.maxLossRun
    reference.handovers
    reference.phyLoss
    reference.handoverLoss
    reference.outageLoss
    reference.pending
];

restored = [
    M.generatedPackets
    M.receivedPackets
    M.lostPackets
    M.packetLossRatio
    M.onTimeDeliveryRate_pct
    M.maxConsecutiveLoss
    sum(env.handovers)
    M.phyLossPackets
    M.handoverLossPackets
    M.outageLossPackets
    M.pendingPackets
];

difference = abs(original - restored);

passed = difference < 1e-8;

comparison = table( ...
    metric, original, restored, ...
    difference, passed);

disp(comparison);

assert(all(passed), ...
    'Restored GSL evaluation differs from original.');

fprintf('Original GSL result comparison: PASS\n');

%% 10. Convert actual GSL packets

fprintf('\n[STEP 7/10] Converting GSL packets...\n');

receivedMask = logical(P.received);

gslPackets = P(receivedMask, { ...
    'packetID', ...
    'generationTime_s', ...
    'arrivalTime_s', ...
    'destinationSatelliteID', ...
    'onTime', ...
    'latency_ms'});

assert(height(gslPackets) == ...
    M.receivedPackets);

assert(numel(unique(gslPackets.packetID)) ...
    == height(gslPackets));

satIDs = double(gslPackets.destinationSatelliteID);

assert(all(isfinite(satIDs)));
assert(all(satIDs == fix(satIDs)));
assert(all(satIDs >= 1));
assert(all(satIDs <= totalSatellites));

gslPackets.p = G.planeIndex(satIDs);

gslPackets.s = G.satelliteInPlane(satIDs);

expectedID = ...
    gslPackets.p * satsPerPlane ...
    + gslPackets.s + 1;

assert(all(expectedID == satIDs));

commonPackets = makeCommonPackets( ...
    gslPackets, ...
    C.packetSize_bytes, ...
    numPlanes, ...
    satsPerPlane);

assert(height(commonPackets) == ...
    M.receivedPackets);

assert(isequal( ...
    sort(double(commonPackets.packet_id)), ...
    sort(double(gslPackets.packetID))));

assert(height(P) == ...
    height(commonPackets) + M.lostPackets);

assert(height(commonPackets) > 0, ...
    'No GSL packets available for this Mock test.');

uniqueSourceSatellites = ...
    numel(unique(commonPackets.source_sat_id));

fprintf('Common packets: %d\n', height(commonPackets));

fprintf('Unique ISL source satellites: %d\n', ...
    uniqueSourceSatellites);

fprintf('Common packet conversion: PASS\n');

%% 11. Create output directory

runID = char(datetime('now', ...
    'Format','yyyyMMdd_HHmmss_SSS'));

folderName = sprintf( ...
    'static_%dx%d_%s_%d_%s', ...
    numPlanes, satsPerPlane, ...
    char(gslPolicy), seed, runID);

runDir = fullfile( ...
    integrationDir, 'results', folderName);

mkdir(runDir);

inputFile = fullfile(runDir, 'common_packets.csv');

resultFile = fullfile(runDir, 'isl_result.csv');

%% 12. Export and verify CSV

writetable(commonPackets, inputFile);

assert(isfile(inputFile));

csvPackets = readtable(inputFile);

assertCommonPacketEquality( ...
    commonPackets, csvPackets);

fprintf('CSV roundtrip: PASS\n');

%% 13. Check Python environment

fprintf('\n[STEP 8/10] Running Python Mock ISL...\n');

pythonExe = getenv('GSL_ISL_PYTHON');

if isempty(pythonExe)

    if ispc
        pythonExe = 'python';
    else
        pythonExe = 'python3';
    end

end

[status, output] = system( ...
    sprintf('"%s" --version', pythonExe));

assert(status == 0, output);

disp(output);

[status, output] = system(sprintf( ...
    '"%s" -c "import numpy; import pandas"', ...
    pythonExe));

assert(status == 0, output);

fprintf('Python environment: PASS\n');

%% 14. Execute Python Mock ISL

command = sprintf( ...
    ['"%s" "%s" --input "%s" --output "%s" ' ...
     '--num-planes %d --sats-per-plane %d'], ...
    pythonExe, ...
    scriptFile, ...
    inputFile, ...
    resultFile, ...
    numPlanes, ...
    satsPerPlane);

islTimer = tic;

[status, output] = system(command);

islExecutionTime_s = toc(islTimer);

disp(output);

assert(status == 0, ...
    'Python Mock ISL execution failed.');

assert(isfile(resultFile));

fprintf('Python Mock ISL execution: PASS\n');

%% 15. Import and validate ISL results

fprintf('\n[STEP 9/10] Validating ISL results...\n');

islResult = readtable(resultFile);

assert(height(islResult) == height(commonPackets));

assert(numel(unique(islResult.packet_id)) ...
    == height(islResult));

[found, loc] = ismember( ...
    commonPackets.packet_id, ...
    islResult.packet_id);

assert(all(found));

islResult = islResult(loc,:);

columnNames = commonPackets.Properties.VariableNames;

assert(all(ismember( ...
    columnNames, ...
    islResult.Properties.VariableNames)));

assertCommonPacketEquality( ...
    commonPackets, islResult(:,columnNames));

assert(all(islResult.isl_delivered == 1));

assert(all(abs( ...
    islResult.isl_delay_ms - 10) < 1e-9));

expectedExitTime = ...
    islResult.isl_entry_time_s + 0.010;

assert(all(abs( ...
    islResult.isl_exit_time_s ...
    - expectedExitTime) < 1e-9));

expectedTotalDelay = ...
    (islResult.isl_exit_time_s ...
    - islResult.generation_time_s) * 1000;

assert(all(abs( ...
    islResult.total_delay_ms ...
    - expectedTotalDelay) < 1e-6));

assert(all(string( ...
    islResult.simulation_mode) == "MOCK"));

assert(all(string( ...
    islResult.isl_drop_reason) == "NONE"));

fprintf('Packet ID matching: PASS\n');
fprintf('Original packet integrity: PASS\n');
fprintf('Mock delivery validation: PASS\n');
fprintf('ISL delay validation: PASS\n');
fprintf('Total delay validation: PASS\n');

%% 16. Calculate integrated metrics

fprintf('\n[STEP 10/10] Calculating integrated metrics...\n');

generatedPackets = height(P);

gslReceivedPackets = M.receivedPackets;

gslLostPackets = M.lostPackets;

islInputPackets = height(commonPackets);

deliveredMask = islResult.isl_delivered == 1;

islDeliveredPackets = sum(deliveredMask);

islLostPackets = ...
    islInputPackets - islDeliveredPackets;

totalLostPackets = ...
    generatedPackets - islDeliveredPackets;

assert(gslReceivedPackets == islInputPackets);

assert(totalLostPackets == ...
    gslLostPackets + islLostPackets);

gslPLR_pct = ...
    100 * gslLostPackets / generatedPackets;

islPLR_pct = ...
    100 * islLostPackets / islInputPackets;

totalPLR_pct = ...
    100 * totalLostPackets / generatedPackets;

deliveryRate_pct = ...
    100 * islDeliveredPackets / generatedPackets;

meanGSLDelay_ms = ...
    mean(islResult.gsl_delay_ms(deliveredMask));

meanISLDelay_ms = ...
    mean(islResult.isl_delay_ms(deliveredMask));

meanTotalDelay_ms = ...
    mean(islResult.total_delay_ms(deliveredMask));

maxTotalDelay_ms = ...
    max(islResult.total_delay_ms(deliveredMask));

minTotalDelay_ms = ...
    min(islResult.total_delay_ms(deliveredMask));

%% 17. Overall consecutive packet loss

allPacketIDs = double(P.packetID);

deliveredIDs = double( ...
    islResult.packet_id(deliveredMask));

assert(numel(unique(allPacketIDs)) ...
    == generatedPackets);

assert(isequal(sort(allPacketIDs(:)), ...
    (1:generatedPackets).'));

assert(all(ismember(deliveredIDs, allPacketIDs)));

overallLoss = ~ismember( ...
    (1:generatedPackets).', deliveredIDs);

edges = diff([false; overallLoss; false]);

runStarts = find(edges == 1);

runEnds = find(edges == -1) - 1;

runLengths = runEnds - runStarts + 1;

if isempty(runLengths)

    maxOverallLossRun = 0;
    meanOverallLossRun = 0;

else

    maxOverallLossRun = max(runLengths);
    meanOverallLossRun = mean(runLengths);

end

assert(sum(overallLoss) == totalLostPackets);

assert(sum(runLengths) == totalLostPackets);

assert(maxOverallLossRun == M.maxConsecutiveLoss);

%% 18. Additional burst metrics

lossRunCount = numel(runLengths);

isolatedLossCount = sum(runLengths == 1);

burstCount2 = sum(runLengths >= 2);

burstCount3 = sum(runLengths >= 3);

burstLossPackets2 = ...
    sum(runLengths(runLengths >= 2));

burstLossPackets3 = ...
    sum(runLengths(runLengths >= 3));

assert(lossRunCount == ...
    isolatedLossCount + burstCount2);

assert(burstCount3 <= burstCount2);

assert(burstLossPackets3 <= burstLossPackets2);

fprintf('Integrated packet accounting: PASS\n');
fprintf('Overall consecutive loss validation: PASS\n');
fprintf('Burst loss validation: PASS\n');

%% 19. Build packet-level results

packetID = (1:generatedPackets).';

[found, loc] = ismember(packetID, allPacketIDs);

assert(all(found));

orderedP = P(loc,:);

gslReceived = logical(orderedP.received);

islDelivered = ismember(packetID, deliveredIDs);

assert(all(~islDelivered | gslReceived));

overallDelivered = islDelivered;

overallLost = ~overallDelivered;

gslDelay_ms = nan(generatedPackets,1);

islDelay_ms = nan(generatedPackets,1);

totalDelay_ms = nan(generatedPackets,1);

gslDelay_ms(gslReceived) = ...
    orderedP.latency_ms(gslReceived);

[found, loc] = ismember( ...
    deliveredIDs, packetID);

assert(all(found));

islDelay_ms(loc) = ...
    islResult.isl_delay_ms(deliveredMask);

totalDelay_ms(loc) = ...
    islResult.total_delay_ms(deliveredMask);

lossStage = repmat("NONE", generatedPackets,1);

lossStage(~gslReceived) = "GSL";

lossStage(gslReceived & ~islDelivered) = "ISL";

overallPackets = table( ...
    packetID, ...
    orderedP.generationTime_s, ...
    gslReceived, ...
    islDelivered, ...
    overallDelivered, ...
    overallLost, ...
    gslDelay_ms, ...
    islDelay_ms, ...
    totalDelay_ms, ...
    lossStage, ...
    'VariableNames', { ...
    'packet_id', ...
    'generation_time_s', ...
    'gsl_received', ...
    'isl_delivered', ...
    'overall_delivered', ...
    'overall_lost', ...
    'gsl_delay_ms', ...
    'isl_delay_ms', ...
    'total_delay_ms', ...
    'loss_stage'});

assert(sum(overallPackets.overall_lost) ...
    == totalLostPackets);

assert(sum(overallPackets.loss_stage == "GSL") ...
    == gslLostPackets);

assert(sum(overallPackets.loss_stage == "ISL") ...
    == islLostPackets);

%% 20. Build loss run table

lossRuns = table( ...
    (1:lossRunCount).', ...
    runStarts, ...
    runEnds, ...
    runLengths, ...
    'VariableNames', { ...
    'loss_run_id', ...
    'first_packet_id', ...
    'last_packet_id', ...
    'length'});

%% 21. Build integrated summary

summary = table( ...
    string(policyName), ...
    seed, ...
    string("MOCK"), ...
    numPlanes, ...
    satsPerPlane, ...
    totalSatellites, ...
    generatedPackets, ...
    gslReceivedPackets, ...
    gslLostPackets, ...
    islInputPackets, ...
    islDeliveredPackets, ...
    islLostPackets, ...
    totalLostPackets, ...
    gslPLR_pct, ...
    islPLR_pct, ...
    totalPLR_pct, ...
    deliveryRate_pct, ...
    meanGSLDelay_ms, ...
    meanISLDelay_ms, ...
    meanTotalDelay_ms, ...
    maxTotalDelay_ms, ...
    minTotalDelay_ms, ...
    maxOverallLossRun, ...
    meanOverallLossRun, ...
    lossRunCount, ...
    isolatedLossCount, ...
    burstCount2, ...
    burstCount3, ...
    burstLossPackets2, ...
    burstLossPackets3, ...
    uniqueSourceSatellites, ...
    sum(env.handovers), ...
    updateCountBefore, ...
    updateCountAfter, ...
    gslEvaluationTime_s, ...
    islExecutionTime_s, ...
    'VariableNames', { ...
    'gslPolicy', ...
    'seed', ...
    'simulationMode', ...
    'numPlanes', ...
    'satsPerPlane', ...
    'totalSatellites', ...
    'generatedPackets', ...
    'gslReceivedPackets', ...
    'gslLostPackets', ...
    'islInputPackets', ...
    'islDeliveredPackets', ...
    'islLostPackets', ...
    'totalLostPackets', ...
    'gslPLR_pct', ...
    'islPLR_pct', ...
    'totalPLR_pct', ...
    'deliveryRate_pct', ...
    'meanGSLDelay_ms', ...
    'meanISLDelay_ms', ...
    'meanTotalDelay_ms', ...
    'maxTotalDelay_ms', ...
    'minTotalDelay_ms', ...
    'maxOverallLossRun', ...
    'meanOverallLossRun', ...
    'lossRunCount', ...
    'isolatedLossCount', ...
    'burstCount2', ...
    'burstCount3', ...
    'burstLossPackets2', ...
    'burstLossPackets3', ...
    'uniqueSourceSatellites', ...
    'handovers', ...
    'updateCountBefore', ...
    'updateCountAfter', ...
    'gslEvaluationTime_s', ...
    'islExecutionTime_s'});

%% 22. Export all results

writetable(P, ...
    fullfile(runDir, 'gsl_all_packets.csv'));

writetable(L, ...
    fullfile(runDir, 'gsl_decisions.csv'));

writetable(G.staticSatellites, ...
    fullfile(runDir, 'static_satellites.csv'));

writetable(comparison, ...
    fullfile(runDir, 'gsl_reference_comparison.csv'));

writetable(overallPackets, ...
    fullfile(runDir, 'overall_packets.csv'));

writetable(lossRuns, ...
    fullfile(runDir, 'overall_loss_runs.csv'));

executionTime_s = toc(totalTimer);

summary.executionTime_s = executionTime_s;

writetable(summary, ...
    fullfile(runDir, 'integrated_summary.csv'));

%% 23. Return integrated result structure

R = struct();

R.simulationMode = "MOCK";

R.numPlanes = numPlanes;
R.satsPerPlane = satsPerPlane;
R.totalSatellites = totalSatellites;

R.policy = policyName;
R.seed = seed;

R.options = O;
R.rewardDefinition = D;

R.checkpointFile = modelFile;

R.originalCurveFile = originalCurveFile;
R.localCurveFile = localCurveFile;

R.geometry = G;

R.gslPacketTable = P;
R.gslPacketMetrics = M;
R.gslDecisionTable = L;

R.gslReferenceComparison = comparison;

R.commonPackets = commonPackets;

R.islResult = islResult;

R.overallPackets = overallPackets;

R.lossRuns = lossRuns;

R.summary = summary;

R.updateCountBefore = updateCountBefore;
R.updateCountAfter = updateCountAfter;

R.outputDir = runDir;

R.executionTime_s = executionTime_s;

%% 24. Final summary

fprintf('\n');
fprintf('========================================\n');
fprintf(' STATIC INTEGRATION FINAL RESULT\n');
fprintf('========================================\n');

fprintf('Simulation mode: MOCK\n');

fprintf('Constellation: %d x %d\n', ...
    numPlanes, satsPerPlane);

fprintf('Total satellites: %d\n', totalSatellites);

fprintf('Policy: %s\n', policyName);
fprintf('Seed: %d\n', seed);

fprintf('Generated packets: %d\n', ...
    generatedPackets);

fprintf('GSL received packets: %d\n', ...
    gslReceivedPackets);

fprintf('GSL lost packets: %d\n', ...
    gslLostPackets);

fprintf('ISL input packets: %d\n', ...
    islInputPackets);

fprintf('ISL delivered packets: %d\n', ...
    islDeliveredPackets);

fprintf('ISL lost packets: %d\n', ...
    islLostPackets);

fprintf('Total lost packets: %d\n', ...
    totalLostPackets);

fprintf('GSL PLR: %.6f %%\n', gslPLR_pct);

fprintf('ISL PLR: %.6f %%\n', islPLR_pct);

fprintf('Total PLR: %.6f %%\n', totalPLR_pct);

fprintf('Delivery rate: %.6f %%\n', ...
    deliveryRate_pct);

fprintf('Mean GSL delay: %.6f ms\n', ...
    meanGSLDelay_ms);

fprintf('Mean ISL delay: %.6f ms\n', ...
    meanISLDelay_ms);

fprintf('Mean total delay: %.6f ms\n', ...
    meanTotalDelay_ms);

fprintf('Maximum total delay: %.6f ms\n', ...
    maxTotalDelay_ms);

fprintf('Minimum total delay: %.6f ms\n', ...
    minTotalDelay_ms);

fprintf('Maximum consecutive loss: %d\n', ...
    maxOverallLossRun);

fprintf('Mean consecutive loss: %.6f\n', ...
    meanOverallLossRun);

fprintf('Loss run count: %d\n', lossRunCount);

fprintf('Isolated losses: %d\n', isolatedLossCount);

fprintf('Burst count (>=2): %d\n', burstCount2);

fprintf('Burst count (>=3): %d\n', burstCount3);

fprintf('Burst loss packets (>=2): %d\n', ...
    burstLossPackets2);

fprintf('Burst loss packets (>=3): %d\n', ...
    burstLossPackets3);

fprintf('Unique ISL source satellites: %d\n', ...
    uniqueSourceSatellites);

fprintf('Handovers: %d\n', sum(env.handovers));

fprintf('Training updates before: %d\n', ...
    updateCountBefore);

fprintf('Training updates after: %d\n', ...
    updateCountAfter);

fprintf('GSL evaluation time: %.3f s\n', ...
    gslEvaluationTime_s);

fprintf('ISL execution time: %.3f s\n', ...
    islExecutionTime_s);

fprintf('Total execution time: %.3f s\n', ...
    executionTime_s);

fprintf('Output folder: %s\n', runDir);

fprintf('\nOriginal GSL result comparison: PASS\n');

fprintf('ALL STATIC INTEGRATION VALIDATIONS PASS\n');

fprintf('========================================\n');

end

%% Local validation function

function assertCommonPacketEquality(A, B)

assert(height(A) == height(B), ...
    'Packet count mismatch.');

assert(isequal( ...
    A.Properties.VariableNames, ...
    B.Properties.VariableNames), ...
    'Packet column mismatch.');

names = A.Properties.VariableNames;

for k = 1:numel(names)

    name = names{k};

    a = double(A.(name));
    b = double(B.(name));

    assert(all(isfinite(a(:))));
    assert(all(isfinite(b(:))));

    assert(all(abs(a(:)-b(:)) < 1e-9), ...
        ['Packet data mismatch: ' name]);

end

end
