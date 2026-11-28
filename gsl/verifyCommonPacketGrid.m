
function verifyCommonPacketGrid()

    % Verify generalized GSL-ISL packet interface.

    clc;

    grids = [
         6, 11;
        20, 20;
        36, 36
    ];

    packetSizeBytes = 160;

    gslDir = fileparts(mfilename('fullpath'));
    projectDir = fileparts(gslDir);

    integrationDir = fullfile( ...
        projectDir, 'gsl_isl_integration');

    testDir = fullfile( ...
        integrationDir, 'results', 'grid_validation');

    if ~exist(testDir, 'dir')
        mkdir(testDir);
    end

    pythonExe = getenv('GSL_ISL_PYTHON');

    if isempty(pythonExe)
        if ispc
            pythonExe = 'python';
        else
            pythonExe = 'python3';
        end
    end

    scriptFile = fullfile(integrationDir, 'mock_isl.py');

    fprintf('\n');
    fprintf('========================================\n');
    fprintf(' GSL-ISL GRID INTERFACE VALIDATION\n');
    fprintf('========================================\n');

    totalChecked = 0;

    for k = 1:size(grids, 1)

        numPlanes = grids(k, 1);
        satsPerPlane = grids(k, 2);

        N = numPlanes * satsPerPlane;

        %% 1. Generate synthetic test packets

        packetID = (1:N)';

        destinationSatelliteID = (1:N)';

        p = floor( ...
            (destinationSatelliteID - 1) / satsPerPlane);

        s = mod( ...
            destinationSatelliteID - 1, satsPerPlane);

        generationTime_s = (packetID - 1) / 60;

        latency_ms = repmat(4.0, N, 1);

        arrivalTime_s = ...
            generationTime_s + latency_ms / 1000;

        onTime = ones(N, 1);

        gslPackets = table( ...
            packetID, ...
            generationTime_s, ...
            arrivalTime_s, ...
            destinationSatelliteID, ...
            onTime, ...
            latency_ms, ...
            p, s);

        %% 2. MATLAB common interface

        T = makeCommonPackets( ...
            gslPackets, packetSizeBytes, ...
            numPlanes, satsPerPlane);

        assert(height(T) == N);
        assert(width(T) == 9);

        assert(all(T.source_sat_id == (1:N)'));

        assert(all(T.p_zero_based == p));
        assert(all(T.s_zero_based == s));

        assert(T.p_zero_based(end) == numPlanes - 1);
        assert(T.s_zero_based(end) == satsPerPlane - 1);

        %% 3. Verify default compatibility

        if numPlanes == 6 && satsPerPlane == 11

            Tdefault = makeCommonPackets( ...
                gslPackets, packetSizeBytes);

            assert(isequal(T, Tdefault), ...
                'Default compatibility failed.');

            fprintf('Default 6x11 compatibility: PASS\n');

        end

        %% 4. Export CSV

        gridName = sprintf( ...
            '%dx%d', numPlanes, satsPerPlane);

        inputFile = fullfile(testDir, ...
            ['common_packets_' gridName '.csv']);

        outputFile = fullfile(testDir, ...
            ['isl_result_' gridName '.csv']);

        writetable(T, inputFile);

        %% 5. Execute Python Mock ISL

        cmd = sprintf( ...
            ['"%s" "%s" --input "%s" --output "%s" ' ...
             '--num-planes %d --sats-per-plane %d'], ...
            pythonExe, scriptFile, ...
            inputFile, outputFile, ...
            numPlanes, satsPerPlane);

        [status, cmdout] = system(cmd);

        fprintf('%s\n', cmdout);

        assert(status == 0, ...
            'Python Mock ISL failed for %s.', gridName);

        %% 6. Validate round trip

        R = readtable(outputFile);

        assert(height(R) == N);
        assert(width(R) == 15);

        commonNames = T.Properties.VariableNames;

        for j = 1:numel(commonNames)

            name = commonNames{j};

            difference = abs( ...
                double(R.(name)) - double(T.(name)));

            assert(all(difference < 1e-9), ...
                'Round-trip mismatch: %s', name);

        end

        assert(all(R.isl_delivered == 1));

        assert(all(abs(R.isl_delay_ms - 10) < 1e-9));

        assert(all(abs(R.total_delay_ms - 14) < 1e-9));

        assert(all(string(R.simulation_mode) == "MOCK"));

        %% 7. Verify invalid mapping rejection

        badPackets = gslPackets;

        badPackets.destinationSatelliteID(1) = 2;

        rejected = false;

        try
            makeCommonPackets( ...
                badPackets, packetSizeBytes, ...
                numPlanes, satsPerPlane);
        catch ME
            if contains(ME.message, ...
                    'Satellite ID mapping mismatch')
                rejected = true;
            else
                rethrow(ME);
            end
        end

        assert(rejected, ...
            'MATLAB accepted an invalid satellite mapping.');

        badCommon = T;
        badCommon.source_sat_id(1) = 2;

        badInputFile = fullfile(testDir, ...
            ['invalid_packets_' gridName '.csv']);

        badOutputFile = fullfile(testDir, ...
            ['invalid_result_' gridName '.csv']);

        writetable(badCommon, badInputFile);

        badCmd = sprintf( ...
            ['"%s" "%s" --input "%s" --output "%s" ' ...
             '--num-planes %d --sats-per-plane %d 2>&1'], ...
            pythonExe, scriptFile, ...
            badInputFile, badOutputFile, ...
            numPlanes, satsPerPlane);

        [badStatus, badOutput] = system(badCmd);

        assert(badStatus ~= 0 && ...
            contains(badOutput, ...
            'Satellite ID mapping mismatch'), ...
            'Python invalid mapping rejection failed.');

        fprintf('Invalid mapping rejection: PASS\n');

        totalChecked = totalChecked + N;

        fprintf('\n');
        fprintf('----------------------------------------\n');
        fprintf('Grid: %s\n', gridName);
        fprintf('Checked satellites: %d\n', N);
        fprintf('MATLAB mapping: PASS\n');
        fprintf('Python mapping: PASS\n');
        fprintf('CSV round trip: PASS\n');
        fprintf('Grid validation: PASS\n');
        fprintf('----------------------------------------\n');

    end

    fprintf('\n');
    fprintf('========================================\n');
    fprintf(' ALL GRID VALIDATIONS PASS\n');
    fprintf('========================================\n');
    fprintf('Validated grids: %d\n', size(grids, 1));
    fprintf('Total satellite IDs: %d\n', totalChecked);
    fprintf('Result directory: %s\n', testDir);
    fprintf('========================================\n');

end
