
function R = verifyStaticGSLCheckpoint()

clc;

fprintf('\n');
fprintf('========================================\n');
fprintf(' STATIC GSL CHECKPOINT VALIDATION\n');
fprintf('========================================\n');

%% 1. Project paths

gslDir = fileparts(mfilename('fullpath'));

moduleDir = fullfile( ...
    gslDir, 'static_reward_1128');

addpath(gslDir);
addpath(moduleDir);

setupStaticReward();

%% 2. Checkpoint path

modelDir = fullfile( ...
    moduleDir, ...
    'results_policy_comparison', ...
    '20261128_010145_246');

modelFile = fullfile( ...
    modelDir, ...
    'quadratic_agent_0100.mat');

assert(isfile(modelFile), ...
    'DDQN checkpoint file not found.');

fprintf('\n[STEP 1/8] Loading checkpoint...\n');

A = load(modelFile, 'checkpoint', 'O', 'D');

assert(isfield(A, 'checkpoint'));
assert(isfield(A, 'O'));
assert(isfield(A, 'D'));

O = A.O;
D = A.D;

fprintf('Checkpoint file: PASS\n');
fprintf('Saved options: PASS\n');
fprintf('Saved reward definition: PASS\n');

%% 2-A. Resolve local PHY curve path

originalCurveFile = O.baseConfig.phyToolboxCurveFile;

localCurveFile = fullfile( ...
    gslDir, ...
    'phy_toolbox', ...
    'ar4ja_qpsk_awgn_160B.csv');

assert(isfile(localCurveFile), ...
    'Local PHY curve file not found.');

O.baseConfig.phyToolboxCurveFile = localCurveFile;

fprintf('\nPHY curve path correction:\n');

fprintf('Original: %s\n', originalCurveFile);

fprintf('Local: %s\n', localCurveFile);

fprintf('PHY curve path correction: PASS\n');

%% 2-B. Validate local PHY curve

fprintf('\nChecking local PHY curve...\n');

T = readtable(localCurveFile);

requiredColumns = { ...
    'ebNo_dB', ...
    'PER', ...
    'CWER', ...
    'PER_lower95', ...
    'PER_upper95'};

assert(all(ismember( ...
    requiredColumns, ...
    T.Properties.VariableNames)), ...
    'PHY curve required columns are missing.');

assert(height(T) == 42, ...
    'PHY curve must contain 42 points.');

assert(T.ebNo_dB(1) == -24);

assert(T.ebNo_dB(end) == 16);

assert(all(diff(T.ebNo_dB) > 0));

assert(all(isfinite(T.PER)));

assert(all(T.PER >= 0 & T.PER <= 1));

fprintf('PHY curve points: %d\n', height(T));

fprintf('Eb/N0 range: %.2f to %.2f dB\n', ...
    min(T.ebNo_dB), max(T.ebNo_dB));

fprintf('PHY curve validation: PASS\n');

%% 3. Validate saved configuration

fprintf('\n[STEP 2/8] Checking configuration...\n');

C = O.baseConfig;

numPlanes = C.numPlanes;
satsPerPlane = C.satsPerPlane;

totalSatellites = numPlanes * satsPerPlane;

assert(numPlanes == 6);
assert(satsPerPlane == 11);
assert(totalSatellites == 66);

assert(strcmp(D.name, 'quadratic'));
assert(O.numEpisodes == 100);
assert(C.duration_s == 600);

assert(isempty(intersect( ...
    O.trainingSeeds, ...
    O.evaluationSeeds)));

seed = O.evaluationSeeds(1);

assert(isscalar(O.evaluationQMargins));

margin = O.evaluationQMargins;

assert(abs(margin - 0.02) < 1e-12);

fprintf('Constellation: %d x %d\n', ...
    numPlanes, satsPerPlane);

fprintf('Total satellites: %d\n', ...
    totalSatellites);

fprintf('Reward: %s\n', D.name);

fprintf('Training episodes (saved setting): %d\n', ...
    O.numEpisodes);

fprintf('Evaluation seed: %d\n', seed);

fprintf('Q margin: %.4f\n', margin);

fprintf('Duration: %d s\n', C.duration_s);

fprintf('Packet rate: %d packets/s\n', ...
    C.packetRate_pps);

fprintf('Environment loss: %.2f dB\n', ...
    O.environmentLoss_dB);

fprintf('Configuration validation: PASS\n');

%% 4. Restore trained DDQN

fprintf('\n[STEP 3/8] Restoring DDQN model...\n');

agent = GSLTrendDoubleDQN(O);

agent.restore(A.checkpoint);

updateCountBefore = agent.updateCount;

assert(updateCountBefore > 0, ...
    'Checkpoint has no training updates.');

assert(updateCountBefore == ...
    A.checkpoint.updateCount);

fprintf('Model restoration: PASS\n');

fprintf('Training update count: %d\n', ...
    updateCountBefore);

%% 5. Create static GSL environment

fprintf('\n[STEP 4/8] Creating environment...\n');

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

fprintf('Static environment: PASS\n');
fprintf('Satellite count: PASS\n');
fprintf('Satellite ID mapping: PASS\n');
fprintf('Zero-based coordinates: PASS\n');

fprintf('Visible satellites: %d\n', ...
    G.visibleCount(1));

%% 6. Check DDQN inference

fprintf('\n[STEP 5/8] Checking inference...\n');

S = env.observe();

assert(~isempty(S.ids));

assert(size(S.features, 1) == 11);

q = agent.values(S);

assert(numel(q) == numel(S.ids));

assert(all(isfinite(q(:))));

fprintf('DDQN input features: %d\n', ...
    size(S.features, 1));

fprintf('Candidate satellites: %d\n', ...
    numel(S.ids));

fprintf('Q-value inference: PASS\n');

%% 7. Frozen DDQN evaluation

fprintf('\n[STEP 6/8] Running frozen evaluation...\n');

timer = tic;

while env.time < O.baseConfig.duration_s

    S = env.observe();

    assert(~isempty(S.ids), ...
        'No visible satellite candidates.');

    q = agent.values(S);

    [~, j] = max(q);

    old = find(S.features(4,:) > 0, 1);

    if ~isempty(old) && ...
            q(j) < q(old) + margin

        j = old;

    end

    env.step(S.ids(j));

    if mod(env.time, 100) == 0

        fprintf('Evaluation: %d / %d s\n', ...
            env.time, ...
            O.baseConfig.duration_s);

    end

end

elapsedTime = toc(timer);

updateCountAfter = agent.updateCount;

assert(updateCountBefore == updateCountAfter, ...
    'DDQN weights were updated during evaluation.');

fprintf('Frozen evaluation: PASS\n');
fprintf('No training updates: PASS\n');

%% 8. Extract packet results

fprintf('\n[STEP 7/8] Extracting packet results...\n');

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

fprintf('Packet extraction: PASS\n');
fprintf('Packet count validation: PASS\n');
fprintf('Loss accounting: PASS\n');

fprintf('\nPacket table columns:\n');

disp(P.Properties.VariableNames.');

fprintf('\nPacket table preview:\n');

disp(P(1:min(5,height(P)),:));

fprintf('\nPacket metrics fields:\n');

disp(fieldnames(M));

%% 9. Compare with original saved evaluation

fprintf('\n[STEP 8/8] Comparing original evaluation...\n');

runsFile = fullfile(modelDir, 'runs.csv');

assert(isfile(runsFile), ...
    'Original runs.csv not found.');

originalRuns = readtable(runsFile);

policyName = string(sprintf( ...
    '%s_Q%g', D.name, margin));

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
    'Restored evaluation differs from original.');

fprintf('Original evaluation comparison: PASS\n');

%% 10. Return validation results

R = struct();

R.packetTable = P;
R.packetMetrics = M;
R.decisionTable = L;
R.geometry = G;

R.options = O;
R.rewardDefinition = D;

R.seed = seed;
R.policy = policyName;
R.comparison = comparison;

R.checkpointFile = modelFile;

R.originalCurveFile = originalCurveFile;
R.localCurveFile = localCurveFile;

R.updateCountBefore = updateCountBefore;
R.updateCountAfter = updateCountAfter;

R.executionTime_s = elapsedTime;

%% 11. Final summary

fprintf('\n');
fprintf('========================================\n');
fprintf(' STATIC GSL VALIDATION RESULT\n');
fprintf('========================================\n');

fprintf('Constellation: %d x %d\n', ...
    numPlanes, satsPerPlane);

fprintf('Policy: %s\n', policyName);

fprintf('Evaluation seed: %d\n', seed);

fprintf('PHY curve: %s\n', localCurveFile);

fprintf('Generated packets: %d\n', ...
    M.generatedPackets);

fprintf('Received packets: %d\n', ...
    M.receivedPackets);

fprintf('Lost packets: %d\n', ...
    M.lostPackets);

fprintf('Packet loss ratio: %.6f %%\n', ...
    M.packetLossRatio);

fprintf('Maximum consecutive loss: %d\n', ...
    M.maxConsecutiveLoss);

fprintf('Handovers: %d\n', ...
    sum(env.handovers));

fprintf('Training updates before: %d\n', ...
    updateCountBefore);

fprintf('Training updates after: %d\n', ...
    updateCountAfter);

fprintf('Evaluation time: %.3f s\n', ...
    elapsedTime);

fprintf('PHY curve path correction: PASS\n');

fprintf('Original result comparison: PASS\n');

fprintf('ALL STATIC GSL VALIDATIONS PASS\n');

fprintf('========================================\n');

end
