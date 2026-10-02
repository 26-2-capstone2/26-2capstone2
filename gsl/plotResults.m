function plotResults(G,CFG)
% Elevation envelope is descriptive; it is NOT a serving-satellite history.
f = figure('Name','Stage 1 - Elevation and visibility','Color','w');
tiledlayout(3,1);
nexttile;
plot(G.time_s,G.maxElevation_deg,'LineWidth',1.4); hold on;
yline(CFG.minElevation_deg,'--','Minimum elevation');
% Follow one fixed satellite to make individual motion/pass variation clear.
[~,exampleIndex] = max(G.elevation_deg(1,:));
plot(G.time_s,G.elevation_deg(:,exampleIndex),'LineWidth',1);
ylabel('Elevation (deg)'); grid on;
legend('Maximum across constellation',sprintf('%g deg mask',CFG.minElevation_deg), ...
    sprintf('Fixed satellite index %d',exampleIndex),'Location','best');
nexttile; stairs(G.time_s,G.visibleCount,'LineWidth',1.2);
ylabel('Visible satellites'); grid on;
nexttile; stairs(G.time_s,double(G.hasCandidate),'LineWidth',1.2);
ylim([-0.1 1.1]); yticks([0 1]); ylabel('Any candidate'); xlabel('Time (s)'); grid on;
if CFG.exportResults
    exportgraphics(f,fullfile(CFG.outputDir,'visibility.png'),'Resolution',150);
end
% Offline ECEF snapshot supplements the interactive geographic viewer.
f3 = figure('Name','Stage 1 - ECEF snapshot','Color','w');
[x,y,z] = sphere(80);
a = CFG.earthEquatorialRadius_m/1e3;
b = a*(1-1/298.257223563); % WGS84 flattening
surf(a*x,a*y,b*z,'FaceColor',[0.18 0.35 0.55],'EdgeColor','none'); hold on;
p = G.positionStartECEF_m/1e3;
scatter3(p(1,:),p(2,:),p(3,:),5,[0.65 0.65 0.65],'filled');
vis = G.isVisible(1,:);
scatter3(p(1,vis),p(2,vis),p(3,vis),28,[0.2 0.8 0.3],'filled');
lat = deg2rad(CFG.gsLatitude_deg); lon = deg2rad(CFG.gsLongitude_deg);
e2 = 1-(b/a)^2; N = a/sqrt(1-e2*sin(lat)^2); h = CFG.gsAltitude_m/1e3;
g = [(N+h)*cos(lat)*cos(lon);(N+h)*cos(lat)*sin(lon); ...
    (N*(1-e2)+h)*sin(lat)];
scatter3(g(1),g(2),g(3),75,[1 0.2 0.1],'filled');
for k = find(vis)
    plot3([g(1) p(1,k)],[g(2) p(2,k)],[g(3) p(3,k)],'Color',[0.2 0.8 0.3]);
end
axis equal; grid on; xlabel('ECEF X (km)'); ylabel('ECEF Y (km)'); zlabel('ECEF Z (km)');
view(CFG.gsLongitude_deg+90,CFG.gsLatitude_deg);
title(sprintf('Initial snapshot: %d satellites, %d visible',numel(vis),sum(vis)));
if CFG.exportResults
    exportgraphics(f3,fullfile(CFG.outputDir,'environment_3d.png'),'Resolution',150);
end
end
