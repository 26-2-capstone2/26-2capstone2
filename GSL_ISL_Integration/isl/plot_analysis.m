% 실행 분석 그래프 저장 - 한 번의 실행 안에서 지연 분포, 시간 변화, 링크 사용량, 홉 수, 선택 유형, 손실 원인을 보여줌
%
function plot_analysis(Rs, P, pngPath)
% Rs: run_isl_sim 결과들 (cell, 실행 1회 = 1칸)

C = viz_colors();
lineStyles = {'-', '--', ':', '-.'};   % 선이 겹쳐도 구분되도록 실행마다 선 모양도 다르게
nRun = numel(Rs);
labels = cell(1, nRun);
for r = 1:nRun
    labels{r} = sprintf('B (\\epsilon = %.1f)', Rs{r}.epsilon);
end

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [0 0 1700 820]);
try
    theme(fig, 'light');
catch
end
set(fig, 'DefaultAxesFontName', C.font, 'DefaultTextFontName', C.font);
tl = tiledlayout(fig, 2, 4, 'TileSpacing', 'compact', 'Padding', 'compact');

% ---- 1. 패킷별 지연 분포 ----
ax = nexttile(tl); hold(ax, 'on');
edges = 0:1:P.deadline + 20;
for r = 1:nRun
    R = Rs{r};
    reached = R.status == 1 | R.status == 2;
    lat = (R.endTime(reached) - R.genTime(reached)) * P.stepTime * 1e3;
    histogram(ax, lat, edges, 'Normalization', 'probability', 'DisplayStyle', 'stairs', ...
        'EdgeColor', C.series(r, :), 'LineWidth', 2, 'LineStyle', lineStyles{r});
end
xline(ax, P.deadline, '--', '기한', 'Color', C.muted, 'LabelVerticalAlignment', 'middle', ...
    'HandleVisibility', 'off');
style_axes(ax, C);
xlim(ax, [30 P.deadline + 20]);
xlabel(ax, '지연 (ms)'); ylabel(ax, '패킷 비율');
title(ax, '패킷별 지연 분포', 'FontWeight', 'normal');
legend(ax, labels, 'Location', 'northeast', 'Box', 'off');

% ---- 2, 3. 시간에 따른 변화 (10초 단위) ----
win = round(10 / P.stepTime);
nWin = ceil(P.simTime / win);
tMid = ((1:nWin) - 0.5) * win * P.stepTime;
onTimeW = nan(nRun, nWin);
latW = nan(nRun, nWin);
for r = 1:nRun
    R = Rs{r};
    w = min(ceil(R.genTime / win), nWin);
    reached = R.status == 1 | R.status == 2;
    lat = (R.endTime - R.genTime) * P.stepTime * 1e3;
    onTimeW(r, :) = accumarray(w, R.status == 1, [nWin 1], @mean, NaN)';
    latW(r, :) = accumarray(w(reached), lat(reached), [nWin 1], @mean, NaN)';
end

ax = nexttile(tl); hold(ax, 'on');
for r = 1:nRun
    plot(ax, tMid, onTimeW(r, :), lineStyles{r}, 'Color', C.series(r, :), 'LineWidth', 2.5 - 0.5 * (r - 1));
end
style_axes(ax, C);
ylim(ax, [max(0, min(onTimeW(:)) - 0.05), 1.01]);
xlabel(ax, '시간 (s)'); ylabel(ax, '기한 내 도착률');
title(ax, '기한 내 도착률 (10초 단위)', 'FontWeight', 'normal');
legend(ax, labels, 'Location', 'southwest', 'Box', 'off');

ax = nexttile(tl); hold(ax, 'on');
for r = 1:nRun
    plot(ax, tMid, latW(r, :), lineStyles{r}, 'Color', C.series(r, :), 'LineWidth', 2.5 - 0.5 * (r - 1));
end
yline(ax, P.deadline, '--', '기한', 'Color', C.muted, 'HandleVisibility', 'off');
style_axes(ax, C);
ylim(ax, [0 P.deadline * 1.1]);
xlabel(ax, '시간 (s)'); ylabel(ax, '평균 지연 (ms)');
title(ax, '평균 지연 (10초 단위)', 'FontWeight', 'normal');
legend(ax, labels, 'Location', 'southwest', 'Box', 'off');

% ---- 4. 홉 수 분포 ----
ax = nexttile(tl);
reachedHops = cell(1, nRun);
for r = 1:nRun
    R = Rs{r};
    reachedHops{r} = R.hops(R.status == 1 | R.status == 2);
end
hopVals = min(cellfun(@min, reachedHops)):max(cellfun(@max, reachedHops));
counts = zeros(numel(hopVals), nRun);
for r = 1:nRun
    counts(:, r) = histcounts(reachedHops{r}, [hopVals - 0.5, hopVals(end) + 0.5])' / numel(reachedHops{r});
end
b = bar(ax, hopVals, counts, 'grouped', 'EdgeColor', 'none');
for r = 1:nRun
    b(r).FaceColor = C.series(r, :);
end
style_axes(ax, C); ax.XGrid = 'off';
xlabel(ax, '홉 수 (최소 경로 = 10)'); ylabel(ax, '도착 패킷 비율');
title(ax, '홉 수 분포', 'FontWeight', 'normal');
legend(ax, labels, 'Location', 'northeast', 'Box', 'off');

% ---- 5, 6. 링크 사용량 지도 (실행별) ----
for r = 1:min(nRun, 2)
    ax = nexttile(tl);
    draw_link_usage(ax, Rs{r}, P, C);
    title(ax, ['링크 사용량: ' labels{r}], 'FontWeight', 'normal');
end

% ---- 7. 선택 유형 비율 ----
ax = nexttile(tl);
typeNames = {'주 경로', '대체 경로', '우회', '무작위'};
share = zeros(nRun, 4);
for r = 1:nRun
    ct = Rs{r}.decisionLog(:, 23);
    share(r, :) = histcounts(ct, 0.5:1:4.5) / numel(ct) * 100;
end
b = barh(ax, 1:nRun, share, 'stacked', 'EdgeColor', 'w', 'LineWidth', 1.5, 'BarWidth', 0.5);
for k = 1:4
    b(k).FaceColor = C.series(k, :);
end
style_axes(ax, C); ax.YGrid = 'off'; ax.XGrid = 'on';
yticks(ax, 1:nRun); yticklabels(ax, labels); ax.YDir = 'reverse';
xlim(ax, [0 100]); xlabel(ax, '라우팅 결정 비율 (%)');
title(ax, '선택 유형', 'FontWeight', 'normal');
legend(ax, typeNames, 'Location', 'southoutside', 'Orientation', 'horizontal', 'Box', 'off');
for r = 1:nRun
    text(ax, 1, r, sprintf('주 %.1f%%', share(r, 1)), 'Color', 'w', 'FontSize', 9, ...
        'VerticalAlignment', 'middle');
end

% ---- 8. 손실 원인 ----
ax = nexttile(tl);
lossNames = {'목적지 기한 초과', '중간 기한 초과', '큐 오버플로', 'TTL 만료'};
lossCnt = zeros(nRun, 4);
for r = 1:nRun
    lossCnt(r, :) = arrayfun(@(s) sum(Rs{r}.status == s), [2 3 4 5]);
end
b = bar(ax, 1:nRun, lossCnt, 'stacked', 'EdgeColor', 'w', 'LineWidth', 1.5, 'BarWidth', 0.5);
for k = 1:4
    b(k).FaceColor = C.series(k, :);
end
style_axes(ax, C); ax.XGrid = 'off';
xticks(ax, 1:nRun); xticklabels(ax, labels);
ylabel(ax, '손실 패킷 수');
total = sum(lossCnt, 2);
ylim(ax, [0 max(max(total), 1) * 1.25]);
if all(total == 0)
    text(ax, mean([1 nRun]), 0.5, '손실 없음', 'HorizontalAlignment', 'center', ...
        'Color', C.muted, 'FontSize', 12);
end
for r = 1:nRun
    text(ax, r, total(r), sprintf('%d개', total(r)), 'HorizontalAlignment', 'center', ...
        'VerticalAlignment', 'bottom', 'Color', C.text);
end
title(ax, '손실 원인', 'FontWeight', 'normal');
legend(ax, lossNames, 'Location', 'northwest', 'Box', 'off');

title(tl, sprintf('실행 분석 (1초마다 %d개 생성, %.0f초)', P.genRate, P.simTime * P.stepTime), ...
    'FontName', C.font, 'FontSize', 15, 'Color', C.text);
exportgraphics(fig, pngPath, 'Resolution', 120);
close(fig);
end

function draw_link_usage(ax, R, P, C)
% 결정 기록에서 링크별로 지나간 패킷 수를 세서 Grid 위에 색으로 표시
G = R.grid;
D = R.decisionLog(R.decisionLog(:, 24) == 1, :);
link = G.linkId(sub2ind(size(G.hasLink), D(:, 4) + 1, D(:, 5) + 1, D(:, 22)));
use = accumarray(link, 1, [G.numLinks 1]);
maxUse = max(use);

hold(ax, 'on'); axis(ax, 'equal'); axis(ax, 'off');
xlim(ax, [-0.6 P.numPlanes - 0.4]); ylim(ax, [-(P.satsPerPlane - 1) - 0.6 0.6]);
cmap = interp1([0 1], [C.seqLow; C.seqHigh], linspace(0, 1, 256)');
for l = find(G.nextP > 0)'
    [p, s, d] = ind2sub(size(G.hasLink), l);
    u = [G.stepP(d), -G.stepS(d)];
    off = 0.07 * [-u(2), u(1)];
    a = [p - 1, -(s - 1)];
    b0 = a + 0.2 * u + off;
    b1 = a + 0.8 * u + off;
    if use(l) == 0
        plot(ax, [b0(1) b1(1)], [b0(2) b1(2)], '-', 'Color', C.unused, 'LineWidth', 1.5);
    else
        c = cmap(round(use(l) / maxUse * 255) + 1, :);
        plot(ax, [b0(1) b1(1)], [b0(2) b1(2)], '-', 'Color', c, 'LineWidth', 4);
    end
end
[PP, SS] = ndgrid(0:P.numPlanes - 1, 0:P.satsPerPlane - 1);
scatter(ax, PP(:), -SS(:), 70, [1 1 1], 'filled', 'MarkerEdgeColor', C.axis);
scatter(ax, P.srcSat(1), -P.srcSat(2), 110, C.series(1, :), 'filled');
scatter(ax, P.dstSat(1), -P.dstSat(2), 110, C.series(2, :), 'filled');
text(ax, P.srcSat(1), -P.srcSat(2) + 0.35, '출발', 'HorizontalAlignment', 'center', 'FontSize', 9);
text(ax, P.dstSat(1), -P.dstSat(2) - 0.35, '도착', 'HorizontalAlignment', 'center', 'FontSize', 9);
colormap(ax, cmap); clim(ax, [0 maxUse]);
cb = colorbar(ax, 'eastoutside');
cb.Label.String = '지나간 패킷 수';
cb.Color = C.muted;
end

function style_axes(ax, C)
box(ax, 'off');
grid(ax, 'on');
ax.GridColor = C.grid; ax.GridAlpha = 1;
ax.XColor = C.axis; ax.YColor = C.axis;
ax.TickLength = [0 0];
end
