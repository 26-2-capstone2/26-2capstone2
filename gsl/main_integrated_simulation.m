function result = main_integrated_simulation()

    clc;
    totalTimer = tic;

    fprintf('\n');
    fprintf('========================================\n');
    fprintf(' GSL-ISL INTEGRATED SIMULATION\n');
    fprintf(' Simulation mode: MOCK ISL\n');
    fprintf('========================================\n');

    %% 1. Configure paths

    gslDir = fileparts(mfilename('fullpath'));
    projectDir = fileparts(gslDir);

    addpath(gslDir);

    integrationDir = fullfile(projectDir, ...
        'gsl_isl_integration');

    pythonExe = getenv('GSL_ISL_PYTHON');

    if isempty(pythonExe)
        if ispc
            pythonExe = 'python';
        else
            pythonExe = 'python3';
        end
    end

    scriptFile = fullfile(integrationDir, ...
        'mock_isl.py');

    [pythonStatus, pythonVersion] = system( ...
        sprintf('"%s" --version', pythonExe));

    assert(pythonStatus == 0, ...
        'Python executable not found. Check PATH or GSL_ISL_PYTHON.');

    fprintf('Python environment: %s\n', strtrim(pythonVersion));

    [dependencyStatus, dependencyOutput] = system( ...
        sprintf('"%s" -c "import numpy, pandas"', pythonExe));

    assert(dependencyStatus == 0, ...
        'Python dependencies missing: %s', dependencyOutput);

    fprintf('Python dependencies: PASS\n');

    assert(isfile(scriptFile), ...
        'Mock ISL script not found.');

    runID = char(datetime('now', ...
        'Format', 'yyyyMMdd_HHmmss_SSS'));

    runDir = fullfile(integrationDir, ...
        'results', runID);

    if ~isfolder(runDir)
        mkdir(runDir);
    end

    inputFile = fullfile(runDir, ...
        'common_packets.csv');

    resultFile = fullfile(runDir, ...
        'isl_result.csv');

    %% 2. Run GSL simulation

    fprintf('\n[STEP 1/7] Running GSL simulation...\n');

    C = configGSL();

    C.makePlots = false;
    C.openPacketViewer = false;
    C.exportResults = true;

    C.outputDir = fullfile(runDir, 'gsl_results');

    gslResult = main_gsl_link_interface([], C);

    generatedPackets = height(gslResult.packetTable);

    receivedPackets = ...
        gslResult.packetMetrics.receivedPackets;

    fprintf('Generated packets: %d\n', ...
        generatedPackets);

    fprintf('GSL received packets: %d\n', ...
        receivedPackets);

    %% 3. Convert common packets

    fprintf('\n[STEP 2/7] Converting common packets...\n');

    gslInputFile = fullfile(gslResult.outputDir, ...
        'isl_input_packets.csv');

    assert(isfile(gslInputFile), ...
        'GSL packet CSV not found.');

    gslPackets = readtable(gslInputFile);

    assert(height(gslPackets) == receivedPackets, ...
        'GSL received packet count mismatch.');

    packetSizeBytes = 160;

    commonPackets = makeCommonPackets( ...
        gslPackets, packetSizeBytes);

    %% 4. Export common packet CSV

    fprintf('\n[STEP 3/7] Exporting common CSV...\n');

    writetable(commonPackets, inputFile);

    checkPackets = readtable(inputFile);

    assert(height(checkPackets) == ...
        height(commonPackets), ...
        'CSV packet count mismatch.');

    assert(isequal( ...
        checkPackets.Properties.VariableNames, ...
        commonPackets.Properties.VariableNames), ...
        'CSV column mismatch.');

    assert(all(abs( ...
        double(table2array(checkPackets)) - ...
        double(table2array(commonPackets))) ...
        < 1e-9, 'all'), ...
        'CSV data integrity mismatch.');

    fprintf('Common CSV export: PASS\n');

    %% 5. Run Python Mock ISL

    fprintf('\n[STEP 4/7] Running Python Mock ISL...\n');

    command = sprintf( ...
        '"%s" "%s" --input "%s" --output "%s"', ...
        pythonExe, scriptFile, inputFile, resultFile);

    [status, output] = system(command);

    disp(output);

    assert(status == 0, ...
        'Python Mock ISL execution failed.');

    assert(isfile(resultFile), ...
        'ISL result CSV not found.');

    %% 6. Load ISL results

    fprintf('\n[STEP 5/7] Loading ISL results...\n');

    islResult = readtable(resultFile);

    fprintf('Returned packets: %d\n', ...
        height(islResult));

    %% 7. Validate round-trip data

    fprintf('\n[STEP 6/7] Validating round trip...\n');

    assert(height(islResult) == ...
        height(commonPackets), ...
        'ISL packet count mismatch.');

    assert(numel(unique(islResult.packet_id)) == ...
        height(islResult), ...
        'Duplicate ISL packet IDs.');

    [found, idx] = ismember( ...
        commonPackets.packet_id, ...
        islResult.packet_id);

    assert(all(found), ...
        'Missing packet IDs.');

    matchedResult = islResult(idx, :);

    % Validate all original common packet columns

    commonColumns = ...
        commonPackets.Properties.VariableNames;

    assert(all(ismember(commonColumns, ...
        matchedResult.Properties.VariableNames)), ...
        'Missing common packet columns.');

    originalData = ...
        double(table2array(commonPackets));

    returnedData = double(table2array( ...
        matchedResult(:, commonColumns)));

    assert(all(abs(originalData - returnedData) ...
        < 1e-9, 'all'), ...
        'Round-trip data integrity mismatch.');

    % Validate Mock ISL delivery

    assert(all(matchedResult.isl_delivered == 1), ...
        'Unexpected Mock ISL packet loss.');

    assert(all(abs( ...
        matchedResult.isl_delay_ms - 10) ...
        < 1e-9), ...
        'Mock ISL delay mismatch.');

    expectedExitTime = ...
        matchedResult.isl_entry_time_s + ...
        matchedResult.isl_delay_ms / 1000;

    assert(all(abs( ...
        matchedResult.isl_exit_time_s - ...
        expectedExitTime) < 1e-9), ...
        'ISL exit time mismatch.');

    expectedTotalDelay = ...
        (matchedResult.isl_exit_time_s - ...
        matchedResult.generation_time_s) * 1000;

    assert(all(abs( ...
        matchedResult.total_delay_ms - ...
        expectedTotalDelay) < 0.001), ...
        'Total delay mismatch.');

    assert(all(string( ...
        matchedResult.simulation_mode) == "MOCK"), ...
        'Unexpected simulation mode.');

    fprintf('Packet count validation: PASS\n');
    fprintf('Packet ID validation: PASS\n');
    fprintf('Common data validation: PASS\n');
    fprintf('ISL delivery validation: PASS\n');
    fprintf('Delay validation: PASS\n');
    fprintf('Simulation mode validation: PASS\n');

    %% 8. Calculate integrated metrics

    fprintf('\n[STEP 7/7] Calculating metrics...\n');

    gslLostPackets = ...
        generatedPackets - receivedPackets;

    islInputPackets = height(commonPackets);

    deliveredMask = ...
        matchedResult.isl_delivered == 1;

    islDeliveredPackets = sum(deliveredMask);

    islLostPackets = ...
        islInputPackets - islDeliveredPackets;

    totalLostPackets = ...
        generatedPackets - islDeliveredPackets;

    assert(generatedPackets > 0, ...
        'No generated packets.');

    assert(totalLostPackets == ...
        gslLostPackets + islLostPackets, ...
        'Packet accounting mismatch.');

    gslPLR = ...
        gslLostPackets / generatedPackets * 100;

    if islInputPackets > 0
        islPLR = ...
            islLostPackets / islInputPackets * 100;
    else
        islPLR = NaN;
    end

    totalPLR = ...
        totalLostPackets / generatedPackets * 100;

    deliveryRate = ...
        islDeliveredPackets / generatedPackets * 100;

    % Delay metrics for delivered packets

    delivered = matchedResult(deliveredMask, :);

    meanGSLDelay = mean(delivered.gsl_delay_ms);
    meanISLDelay = mean(delivered.isl_delay_ms);
    meanTotalDelay = mean(delivered.total_delay_ms);

    if isempty(delivered)
        maxTotalDelay = NaN;
        minTotalDelay = NaN;
    else
        maxTotalDelay = max(delivered.total_delay_ms);
        minTotalDelay = min(delivered.total_delay_ms);
    end

    %% 9. Save summary table

    summary = table();

    summary.simulation_mode = "MOCK";
    summary.generated_packets = generatedPackets;
    summary.gsl_received_packets = receivedPackets;
    summary.gsl_lost_packets = gslLostPackets;
    summary.isl_input_packets = islInputPackets;
    summary.isl_delivered_packets = islDeliveredPackets;
    summary.isl_lost_packets = islLostPackets;
    summary.total_lost_packets = totalLostPackets;

    summary.gsl_plr_percent = gslPLR;
    summary.isl_plr_percent = islPLR;
    summary.total_plr_percent = totalPLR;
    summary.delivery_rate_percent = deliveryRate;

    summary.mean_gsl_delay_ms = meanGSLDelay;
    summary.mean_isl_delay_ms = meanISLDelay;
    summary.mean_total_delay_ms = meanTotalDelay;
    summary.max_total_delay_ms = maxTotalDelay;
    summary.min_total_delay_ms = minTotalDelay;

    summary.execution_time_s = toc(totalTimer);

    summaryFile = fullfile(runDir, ...
        'integrated_summary.csv');

    writetable(summary, summaryFile);

    %% 10. Print final results

    fprintf('\n');
    fprintf('========================================\n');
    fprintf(' INTEGRATED SIMULATION RESULT\n');
    fprintf('========================================\n');

    fprintf('Simulation mode       : MOCK\n');
    fprintf('Generated packets     : %d\n', ...
        generatedPackets);

    fprintf('GSL received packets  : %d\n', ...
        receivedPackets);

    fprintf('GSL lost packets      : %d\n', ...
        gslLostPackets);

    fprintf('ISL delivered packets : %d\n', ...
        islDeliveredPackets);

    fprintf('ISL lost packets      : %d\n', ...
        islLostPackets);

    fprintf('Total lost packets    : %d\n', ...
        totalLostPackets);

    fprintf('----------------------------------------\n');

    fprintf('GSL PLR               : %.6f %%\n', ...
        gslPLR);

    fprintf('ISL PLR               : %.6f %%\n', ...
        islPLR);

    fprintf('Total PLR             : %.6f %%\n', ...
        totalPLR);

    fprintf('Delivery rate         : %.6f %%\n', ...
        deliveryRate);

    fprintf('----------------------------------------\n');

    fprintf('Mean GSL delay        : %.6f ms\n', ...
        meanGSLDelay);

    fprintf('Mean ISL delay        : %.6f ms\n', ...
        meanISLDelay);

    fprintf('Mean total delay      : %.6f ms\n', ...
        meanTotalDelay);

    fprintf('Max total delay       : %.6f ms\n', ...
        maxTotalDelay);

    fprintf('Min total delay       : %.6f ms\n', ...
        minTotalDelay);

    fprintf('----------------------------------------\n');

    fprintf('Execution time        : %.3f s\n', ...
        summary.execution_time_s);

    fprintf('Result directory      : %s\n', ...
        runDir);

    fprintf('All validations       : PASS\n');
    fprintf('========================================\n');

    %% 11. Return results

    result = struct();

    result.gslResult = gslResult;
    result.commonPackets = commonPackets;
    result.islResult = matchedResult;
    result.summary = summary;
    result.outputDir = runDir;
    result.simulationMode = "MOCK";

end