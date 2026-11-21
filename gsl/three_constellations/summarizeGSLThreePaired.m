function paired=summarizeGSLThreePaired(R)
paired=table();fields={'loss_pct','maxLossRun','onTime_pct','handovers'};
for k=1:3
    for baseline=["MaxSNR","MaxSNR_Hysteresis"]
        a=R.runs(R.runs.planes==R.options.sizes(k,1)&R.runs.satellitesPerPlane==R.options.sizes(k,2)&R.runs.policy=="DDQN",:);
        b=R.runs(R.runs.planes==R.options.sizes(k,1)&R.runs.satellitesPerPlane==R.options.sizes(k,2)&R.runs.policy==baseline,:);
        a=sortrows(a,'seed');b=sortrows(b,'seed');assert(isequal(a.seed,b.seed));n=height(a);
        for j=1:numel(fields)
            name=fields{j}; delta=a.(name)-b.(name); sd=std(delta); center=mean(delta);
            lower=NaN;upper=NaN;
            if n>1
                df=n-1;critical=sqrt(df*(1/betaincinv(.05,df/2,.5)-1));
                half=critical*sd/sqrt(n);lower=center-half;upper=center+half;
            end
            row=table(string(sprintf('%dx%d',R.options.sizes(k,1),R.options.sizes(k,2))),baseline,string(name),n,center,sd,lower,upper, ...
                'VariableNames',{'constellation','baseline','metric','pairedSeeds','ddqnMinusBaseline_mean','delta_std','meanDelta_lower95','meanDelta_upper95'});
            paired=[paired;row]; %#ok<AGROW>
        end
    end
end
writetable(paired,fullfile(R.outputDir,'paired_differences.csv'));
end
