function f=plotMovingGSLGrid(C)
% Reference-sphere arc coordinates of the common moving grid.
f=figure('Name','GSL Moving Grid Layout','Color','w','Position',[100 120 1200 440]);
a=axes(f); hold(a,'on'); colors=lines(3);
passTime=C.gridPassTime_s;
if isempty(passTime), passTime=C.duration_s/2; end
times=[0 passTime C.duration_s];
p=(0:C.numPlanes-1)-(C.numPlanes-1)/2;
s=(0:C.satsPerPlane-1)-(C.satsPerPlane-1)/2;
for k=1:3
    x=s*C.gridAlongSpacing_m/1000+C.gridCenterSpeed_mps*(times(k)-passTime)/1000;
    y=p*C.gridCrossSpacing_m/1000;
    for row=1:numel(p)
        plot(a,x,repmat(y(row),size(x)),'-o','Color',colors(k,:), ...
            'MarkerSize',3,'HandleVisibility','off');
    end
    for column=1:numel(s)
        plot(a,repmat(x(column),size(y)),y,'-','Color',colors(k,:),'HandleVisibility','off');
    end
    plot(a,NaN,NaN,'-o','Color',colors(k,:),'DisplayName',sprintf('t = %.0f s',times(k)));
end
plot(a,0,0,'rp','MarkerFaceColor','r','MarkerSize',14,'DisplayName','Ground station projection');
xlabel(a,'Along-track reference arc [km]'); ylabel(a,'Cross-track reference arc [km]');
title(a,sprintf('Experimental moving %d x %d grid | spacing %.0f / %.0f km | center speed %.1f km/s', ...
    C.numPlanes,C.satsPerPlane,C.gridCrossSpacing_m/1000,C.gridAlongSpacing_m/1000,C.gridCenterSpeed_mps/1000));
legend(a,'Location','bestoutside'); grid(a,'on');
end
