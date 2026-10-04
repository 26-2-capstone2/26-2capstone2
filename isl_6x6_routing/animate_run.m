% 애니메이션 저장 - 링크 큐 점유율과 패킷 이동을 GIF로 만듦
%
function animate_run(R, P, gifPath)
% 시뮬레이션 1회를 GIF 애니메이션으로 저장
% 왼쪽: Grid 링크 큐 점유율(색) + 링크 위 전송 중 패킷(점)
% 오른쪽 위: 누적 생성/도착/손실, 오른쪽 아래: 출발 위성 링크 큐 길이

G = R.grid;
animSteps = size(R.animQueue, 2);
font = 'Malgun Gothic';

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [0 0 1200 620]);
try
    theme(fig, 'light');   % R2025a 이후 기본 다크 테마 방지
catch
end
set(fig, 'DefaultAxesFontName', font, 'DefaultTextFontName', font);

% ---- Grid ----
ax = axes(fig, 'Position', [0.03 0.06 0.5 0.84]);
hold(ax, 'on'); axis(ax, 'equal'); axis(ax, 'off');
xlim(ax, [-0.7 P.numPlanes - 0.3]);
ylim(ax, [-(P.satsPerPlane - 1) - 0.7 0.7]);

cpts = [0 0.85 0.85 0.85; 0.02 0.3 0.75 0.3; 0.5 1 0.8 0; 0.8 1 0.45 0; 1 0.85 0.1 0.1];
cmap = interp1(cpts(:, 1), cpts(:, 2:4), linspace(0, 1, 256)');

valid = find(G.nextP > 0);
hL = gobjects(numel(valid), 1);
mid = zeros(numel(valid), 2);
for i = 1:numel(valid)
    l = valid(i);
    [p, s, d] = ind2sub([P.numPlanes P.satsPerPlane 4], l);
    u = [G.stepP(d), -G.stepS(d)];
    off = 0.07 * [-u(2), u(1)];
    a = [p - 1, -(s - 1)];
    b0 = a + 0.2 * u + off;
    b1 = a + 0.8 * u + off;
    hL(i) = plot(ax, [b0(1) b1(1)], [b0(2) b1(2)], '-', 'LineWidth', 4, 'Color', cmap(1, :));
    mid(i, :) = a + 0.55 * u + off;
end

[PP, SS] = ndgrid(0:P.numPlanes - 1, 0:P.satsPerPlane - 1);
scatter(ax, PP(:), -SS(:), 260, [0.8 0.88 1], 'filled', 'MarkerEdgeColor', [0.4 0.5 0.7]);
scatter(ax, P.srcSat(1), -P.srcSat(2), 320, [0.2 0.6 1], 'filled', 'MarkerEdgeColor', 'k');
scatter(ax, P.dstSat(1), -P.dstSat(2), 320, [1 0.4 0.4], 'filled', 'MarkerEdgeColor', 'k');
text(ax, P.srcSat(1), -P.srcSat(2) + 0.32, '출발', 'HorizontalAlignment', 'center', 'FontSize', 9);
text(ax, P.dstSat(1), -P.dstSat(2) - 0.32, '도착', 'HorizontalAlignment', 'center', 'FontSize', 9);
for p = 0:P.numPlanes - 1
    text(ax, p, 0.5, sprintf('p=%d', p), 'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', [0.4 0.4 0.4]);
end
for s = 0:P.satsPerPlane - 1
    text(ax, -0.55, -s, sprintf('s=%d', s), 'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', [0.4 0.4 0.4]);
end
hF = scatter(ax, nan, nan, 10, [0.1 0.1 0.45], 'filled');

colormap(ax, cmap);
clim(ax, [0 1]);
cb = colorbar(ax, 'eastoutside');
cb.Label.String = '링크 큐 점유율 (큐 길이 / 100)';
hT = title(ax, '', 'FontSize', 12);

% ---- 누적 패킷 수 ----
ax2 = axes(fig, 'Position', [0.62 0.57 0.35 0.33]);
hold(ax2, 'on'); grid(ax2, 'on'); box(ax2, 'on');
timeline = R.timeline(1:animSteps, :);
lost = sum(timeline(:, 3:6), 2);
hG = plot(ax2, nan, nan, 'k-', 'LineWidth', 1.5);
hO = plot(ax2, nan, nan, '-', 'Color', [0.2 0.6 0.2], 'LineWidth', 1.5);
hX = plot(ax2, nan, nan, '-', 'Color', [0.85 0.1 0.1], 'LineWidth', 1.5);
xlim(ax2, [0 animSteps]); ylim(ax2, [0 max(timeline(end, 1), 1) * 1.05]);
xlabel(ax2, 'step (ms)'); ylabel(ax2, '누적 패킷 수');
legend(ax2, {'생성', '기한 내 도착', '손실'}, 'Location', 'northwest');
title(ax2, '누적 패킷');

% ---- 출발 위성 링크 큐 ----
ax3 = axes(fig, 'Position', [0.62 0.08 0.35 0.33]);
hold(ax3, 'on'); grid(ax3, 'on'); box(ax3, 'on');
lR = G.linkId(G.srcSat(1), G.srcSat(2), 4);
lD = G.linkId(G.srcSat(1), G.srcSat(2), 2);
qR = double(R.animQueue(lR, :));
qD = double(R.animQueue(lD, :));
hR = plot(ax3, nan, nan, '-', 'Color', [0.1 0.4 0.8], 'LineWidth', 1.5);
hDn = plot(ax3, nan, nan, '-', 'Color', [0.9 0.5 0.1], 'LineWidth', 1.5);
yline(ax3, P.queueMax, 'k:');
xlim(ax3, [0 animSteps]); ylim(ax3, [0 P.queueMax * 1.1]);
xlabel(ax3, 'step (ms)'); ylabel(ax3, '큐 길이 (packets)');
legend(ax3, {'우 (주 경로)', '하 (대체 경로)'}, 'Location', 'northwest');
title(ax3, '출발 위성 (0,0) 링크 큐');

% ---- 프레임 ----
first = true;
for t = 1:P.animFrameInterval:animSteps
    q = double(R.animQueue(valid, t)) / P.queueMax;
    ci = round(q * 255) + 1;
    for i = 1:numel(valid)
        hL(i).Color = cmap(ci(i), :);
    end
    f = double(R.animInFlight(valid, t));
    on = f > 0;
    set(hF, 'XData', mid(on, 1), 'YData', mid(on, 2), 'SizeData', 12 + 5 * f(on));

    set(hG, 'XData', 1:t, 'YData', timeline(1:t, 1));
    set(hO, 'XData', 1:t, 'YData', timeline(1:t, 2));
    set(hX, 'XData', 1:t, 'YData', lost(1:t));
    set(hR, 'XData', 1:t, 'YData', qR(1:t));
    set(hDn, 'XData', 1:t, 'YData', qD(1:t));

    hT.String = sprintf('B 라우팅 | 생성률 %d packets/s, \\epsilon = %.1f | t = %d ms', ...
        R.genRate, R.epsilon, t);
    drawnow;

    img = frame2im(getframe(fig));
    [A, map] = rgb2ind(img, 128);
    if first
        imwrite(A, map, gifPath, 'gif', 'LoopCount', Inf, 'DelayTime', 0.08);
        first = false;
    else
        imwrite(A, map, gifPath, 'gif', 'WriteMode', 'append', 'DelayTime', 0.08);
    end
end
close(fig);
end
