% 메인 실행 파일 - 전체 시뮬레이션을 돌리고 결과(CSV, GIF, PNG)를 results 폴더에 저장 

% ISL 2D Grid B 라우팅 시뮬레이션 실행
% 생성률 x ε 2종류 실행
%   ε = 0   : 성능 측정용 -> 지표, 애니메이션
%   ε = 0.1 : 데이터 수집용 -> 강화학습용 결정 기록 / 패킷 기록 CSV

P = config_isl();
baseDir = fileparts(mfilename('fullpath'));
outDir = fullfile(baseDir, 'results');
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

logColumns = {'step', 'packet_id', 'hop', 'cur_p', 'cur_s', ...
    'q_up', 'q_down', 'q_left', 'q_right', ...
    'L_up', 'L_down', 'L_left', 'L_right', ...
    'N_up', 'N_down', 'N_left', 'N_right', ...
    'rem_dp', 'rem_ds', 'rem_deadline', 'ttl', ...
    'action', 'choice_type', 'enqueued'};
% action: 1 상, 2 하, 3 좌, 4 우 / choice_type: 1 주, 2 대체, 3 우회, 4 무작위
pktColumns = {'packet_id', 'gen_step', 'end_step', 'result', 'hops'};
% result: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료

results = {};
runs = {};   % 실행 분석 그래프용 (실행 결과 전체)
for epsilon = P.epsilonList
    for genRate = P.genRate
        tic;
        R = run_isl_sim(P, genRate, epsilon, P.randomSeed, epsilon == 0);
        M = compute_metrics(R, P);
        results{end+1} = M; %#ok<SAGROW>
        runs{end+1} = R; %#ok<SAGROW>
        tag = sprintf('rate%dpps_eps%.1f', genRate, epsilon);

        writetable(array2table([(0:R.numPackets-1)', R.genTime, R.endTime, R.status, R.hops], ...
            'VariableNames', pktColumns), fullfile(outDir, ['packet_log_' tag '.csv']));
        if epsilon > 0
            writetable(array2table(R.decisionLog, 'VariableNames', logColumns), ...
                fullfile(outDir, ['decision_log_' tag '.csv']));
        else
            animate_run(R, P, fullfile(outDir, ['anim_' tag '.gif']));
        end

        fprintf('[%s] steps=%d gen=%d onTime=%.3f loss=%.3f lat=%.1fms hops=%.2f decisions=%d (%.1fs)\n', ...
            tag, R.endStep, R.numPackets, M.onTimeRate, M.lossRate, M.avgLatency_ms, M.avgHops, ...
            size(R.decisionLog, 1), toc);
    end
end

T = struct2table([results{:}]);
writetable(T, fullfile(outDir, 'metrics_summary.csv'));
plot_metrics(T, P, fullfile(outDir, 'metrics_summary.png'));    % 지표 비교
plot_analysis(runs, P, fullfile(outDir, 'run_analysis.png'));   % 실행 분석
disp(T);

% 결과 자동 저장 (코드 .m + 이미지 + CSV) - 실행할 때마다 날짜_시분 폴더를 새로 만듦
saveRoot = 'C:\Users\eun\Desktop\capstone_isl\baseline';   % 저장 경로 
saveDir = fullfile(saveRoot, char(datetime('now', 'Format', 'yyyy-MM-dd_HHmm')));
save_results(baseDir, outDir, saveDir);
