% 지표 비교 그래프 저장 - 지표 7개를 실행(알고리즘·ε)별 막대로 비교 (지표마다 그래프 1개)
%
function plot_metrics(T, P, pngPath)
% T: compute_metrics 결과 표 (실행 1회 = 1줄)
% 나중에 강화학습 결과를 T에 한 줄 추가하면 막대가 하나 늘어나는 구조

C = viz_colors();
fig = figure('Visible', 'off', 'Color', 'w', 'Position', [0 0 1500 680]);
try
    theme(fig, 'light');
catch
end
set(fig, 'DefaultAxesFontName', C.font, 'DefaultTextFontName', C.font);
tl = tiledlayout(fig, 2, 4, 'TileSpacing', 'compact', 'Padding', 'compact');

vars = {'avgLatency_ms', 'lossRate', 'throughput_Mbps', 'onTimeRate', ...
    'maxConsecLoss', 'routeChanges', 'avgHops'};
names = {'Average Latency (ms)', 'Packet Loss Rate', 'Throughput (Mbps)', ...
    'On-time Delivery Rate', 'Consecutive Packet Loss Length', ...
    'Route Change Count', 'Average Hop Count'};
fmt = {'%.1f', '%.4f', '%.4f', '%.4f', '%d', '%d', '%.2f'};

labels = run_labels(T);
n = height(T);
for i = 1:numel(vars)
    ax = nexttile(tl);
    vals = T.(vars{i});
    b = bar(ax, 1:n, vals, 0.55, 'FaceColor', 'flat', 'EdgeColor', 'none');
    b.CData = C.series(1:n, :);
    style_axes(ax, C);
    xticks(ax, 1:n); xticklabels(ax, labels);
    title(ax, names{i}, 'FontWeight', 'normal', 'Color', C.text);
    top = max(vals);
    if top <= 0
        ylim(ax, [0 1]);   % 전부 0이면 축을 0~1로 고정
    else
        ylim(ax, [0 top * 1.25]);
    end
    for j = 1:n
        text(ax, j, vals(j), sprintf(fmt{i}, vals(j)), 'HorizontalAlignment', 'center', ...
            'VerticalAlignment', 'bottom', 'Color', C.text, 'FontSize', 10);
    end
end

% 실행 정보
ax = nexttile(tl);
axis(ax, 'off');
info = {
    '실행 조건'
    sprintf('Grid %d x %d,  (%d,%d) → (%d,%d)', P.numPlanes, P.satsPerPlane, P.srcSat, P.dstSat)
    sprintf('1초마다 생성: %d개,  패킷 %d Byte', P.genRate, P.packetSize)
    sprintf('총 시간: %.0f초 (%d step)', P.simTime * P.stepTime, P.simTime)
    sprintf('생성 패킷: %d개 / 실행', T.generated(1))
    sprintf('B 라우팅: k = %.1f, X = %.1f, Y = %.1f', P.k, P.X, P.Y)
    sprintf('기한 %d ms,  TTL %d', P.deadline, P.ttlInit)
    };
text(ax, 0, 1, info, 'VerticalAlignment', 'top', 'FontSize', 11, 'Color', C.text);

title(tl, '성능 지표 비교', 'FontName', C.font, 'FontSize', 15, 'Color', C.text);
exportgraphics(fig, pngPath, 'Resolution', 120);
close(fig);
end

function labels = run_labels(T)
labels = cell(height(T), 1);
for j = 1:height(T)
    labels{j} = sprintf('B (\\epsilon = %.1f)', T.epsilon(j));
end
end

function style_axes(ax, C)
box(ax, 'off');
grid(ax, 'on');
ax.XGrid = 'off';
ax.GridColor = C.grid; ax.GridAlpha = 1;
ax.XColor = C.axis; ax.YColor = C.axis;
ax.TickLength = [0 0];
end
