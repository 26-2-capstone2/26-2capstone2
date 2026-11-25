function T = makeCommonPackets(gslPackets, packetSizeBytes)

    % GSL-ISL Common Packet Interface V1.0

    %% 1. Check required columns

    required = {
        'packetID'
        'generationTime_s'
        'arrivalTime_s'
        'destinationSatelliteID'
        'onTime'
        'latency_ms'
        'p'
        's'
    };

    assert(istable(gslPackets), ...
        'GSL input must be a table.');

    assert(all(ismember(required, ...
        gslPackets.Properties.VariableNames)), ...
        'Required GSL columns are missing.');

    validateattributes(packetSizeBytes, ...
        {'numeric'}, {'scalar','integer','positive','finite'});

    %% 2. Convert to common packet format

    T = table();

    T.packet_id = gslPackets.packetID;

    T.generation_time_s = ...
        gslPackets.generationTime_s;

    T.isl_entry_time_s = ...
        gslPackets.arrivalTime_s;

    T.source_sat_id = ...
        gslPackets.destinationSatelliteID;

    T.p_zero_based = gslPackets.p;
    T.s_zero_based = gslPackets.s;

    T.packet_size_bytes = ...
        repmat(packetSizeBytes, height(gslPackets), 1);

    T.gsl_on_time = gslPackets.onTime;

    T.gsl_delay_ms = gslPackets.latency_ms;

    %% 3. Validate packet IDs

    assert(all(isfinite(T.packet_id) & ...
        T.packet_id >= 1 & ...
        T.packet_id == fix(T.packet_id)), ...
        'Invalid packet ID.');

    assert(numel(unique(T.packet_id)) == height(T), ...
        'Duplicate packet IDs detected.');

    %% 4. Validate timestamps

    assert(all(isfinite(T.generation_time_s)) && ...
           all(isfinite(T.isl_entry_time_s)), ...
        'Invalid packet timestamp.');

    assert(all(T.generation_time_s >= 0), ...
        'Negative generation time.');

    assert(all(T.isl_entry_time_s >= ...
               T.generation_time_s), ...
        'Invalid ISL entry time.');

    %% 5. Validate satellite IDs

    assert(all(T.source_sat_id >= 1 & ...
               T.source_sat_id <= 66 & ...
               T.source_sat_id == fix(T.source_sat_id)), ...
        'Invalid satellite ID.');

    assert(all(T.p_zero_based >= 0 & ...
               T.p_zero_based <= 5 & ...
               T.p_zero_based == fix(T.p_zero_based)), ...
        'Invalid orbital plane index.');

    assert(all(T.s_zero_based >= 0 & ...
               T.s_zero_based <= 10 & ...
               T.s_zero_based == fix(T.s_zero_based)), ...
        'Invalid satellite index.');

    expectedID = ...
        T.p_zero_based * 11 + T.s_zero_based + 1;

    assert(all(T.source_sat_id == expectedID), ...
        'Satellite ID mapping mismatch.');

    %% 6. Validate GSL delay and status

    assert(all(isfinite(T.gsl_delay_ms) & ...
               T.gsl_delay_ms >= 0), ...
        'Invalid GSL delay.');

    expectedDelay = ...
        (T.isl_entry_time_s - T.generation_time_s) * 1000;

    assert(all(abs(T.gsl_delay_ms - expectedDelay) < 0.001), ...
        'GSL delay mismatch.');

    assert(all(ismember(T.gsl_on_time, [0 1])), ...
        'Invalid GSL delivery status.');

    %% 7. Sort by ISL entry time

    T = sortrows(T, ...
        {'isl_entry_time_s', 'packet_id'});

    %% 8. Print verification result

    fprintf('\n');
    fprintf('===== GSL-ISL COMMON INTERFACE =====\n');
    fprintf('Input packets: %d\n', height(gslPackets));
    fprintf('Output packets: %d\n', height(T));
    fprintf('Packet size: %d Bytes\n', packetSizeBytes);
    fprintf('Packet ID validation: PASS\n');
    fprintf('Timestamp validation: PASS\n');
    fprintf('Satellite ID validation: PASS\n');
    fprintf('GSL delay validation: PASS\n');
    fprintf('Packet sorting: PASS\n');
    fprintf('====================================\n');

end