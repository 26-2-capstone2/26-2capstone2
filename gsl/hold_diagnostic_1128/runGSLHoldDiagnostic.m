function R=runGSLHoldDiagnostic(root,out)
if ~isfolder(out),mkdir(out);end
grids=["6x11","20x20","36x36"];runs=table();pairs=table();windows=struct([]);windowSeconds=10;
for g=1:3
    resultsRoot=fullfile(root,grids(g),'gsl','static_reward_1128','results_policy_comparison');
    pointer=strtrim(fileread(fullfile(resultsRoot,'latest_result.txt')));[~,name]=fileparts(pointer);folder=fullfile(resultsRoot,name);
    saved=load(fullfile(folder,'quadratic_agent_0100.mat'),'checkpoint','O','D');O=saved.O;D=saved.D;
    agent=GSLTrendDoubleDQN(O);agent.restore(saved.checkpoint);updates=agent.updateCount;
    originalWeights=agent.onlineNetwork.Learnables;
    for rep=1:10
        trial=fullfile(folder,'quadratic_Q0.02',sprintf('repeat_%02d',rep));
        E=load(fullfile(trial,'environment.mat'));seed=E.G.layout.episodeSeed;C=E.config;G=E.G;
        P=readtable(fullfile(trial,'packets.csv'));L=readtable(fullfile(trial,'decisions.csv'));
        env=GSLHoldAuditEpisode(C,G,O,seed,D);held=GSLHoldAuditEpisode(C,G,O,seed,D);
        assert(isequal(env.snr,E.snr)&&isequaln(env.per,E.per)&&isequal(env.draws,E.draws));
        assert(isequal(env.snr,held.snr)&&isequal(env.draws,held.draws));
        initialID=choice(agent,env,O.trainingQMargin);n=C.packetRate_pps;
        while env.time<C.duration_s
            t=env.time;id=choice(agent,env,O.trainingQMargin);assert(id==L.servingSatID(t+1));
            current=env.servingID;prior=env.streak;
            if current>0&&id~=current&&t+windowSeconds<=C.duration_s
                forced=copy(env);before=env.observe();
                forced.step(current); % Only this decision is overridden.
                for j=2:windowSeconds,forced.step(choice(agent,forced,O.trainingQMargin));end
                assert(env.time==t&&env.servingID==current&&isequal(before,env.observe()));
                indices=t*n+(1:windowSeconds*n);actual=logical(P.lost(indices));alternative=forced.loss(indices);
                [actualPeak,actualEnd]=windowPeak(actual,prior);[holdPeak,holdEnd]=windowPeak(alternative,prior);
                first=t*n+(1:n);a1=sum(P.lost(first));h1=sum(forced.loss(first));
                S=before;q=agent.values(S);old=find(S.ids==current);next=find(S.ids==id);
                k=height(pairs)+1;
                pair=table(grids(g),rep,seed,t,current,id,prior,env.per(t+1,current),env.per(t+1,id), ...
                    1-min(env.per(t+1,S.ids)),q(old),q(next),a1,h1,sum(actual),sum(alternative), ...
                    actualPeak,holdPeak,sum(L.handoverEvent(t+(1:windowSeconds))),sum(forced.handovers(t+(1:windowSeconds))), ...
                    actualEnd,holdEnd, ...
                    'VariableNames',{'grid','repeat','seed','time_s','currentID','DDQN_ID','priorStreak','currentPER','DDQN_PER','bestSuccess', ...
                    'Q_current','Q_DDQN','DDQN_loss_1s','hold_loss_1s','DDQN_loss_10s','hold_loss_10s','DDQN_peak_10s','hold_peak_10s', ...
                    'DDQN_HO_10s','hold_HO_10s','DDQN_rightCensored','hold_rightCensored'});
                pairs=[pairs;pair]; %#ok<AGROW>
                windows(k).actualLoss=actual;windows(k).holdLoss=alternative;
                windows(k).actualIDs=L.servingSatID(t+(1:windowSeconds));windows(k).holdIDs=forced.selected(t+(1:windowSeconds));
                windows(k).priorStreak=prior; %#ok<AGROW>
            end
            env.step(id);held.step(initialID);
        end
        assert(isequal(env.loss,logical(P.lost))&&isequal(env.selected,L.servingSatID(1:600)));
        [HP,HM,HL]=held.results();assert(all(HL.servingSatID==initialID)&&~any(held.handovers));
        [RP,RM]=env.results();assert(isequal(logical(RP.lost),logical(P.lost)));
        runs=[runs;metricRow(grids(g),"DDQN",rep,seed,RM,env.loss,sum(env.handovers)); ...
            metricRow(grids(g),"hold_initial",rep,seed,HM,held.loss,0)]; %#ok<AGROW>
        target=fullfile(out,grids(g),sprintf('repeat_%02d',rep));mkdir(target);
        writetable(HP,fullfile(target,'hold_packets.csv'));writetable(HM.lossRuns,fullfile(target,'hold_loss_runs.csv'));
        writetable(HL,fullfile(target,'hold_decisions.csv'));
        sample=struct('grid',grids(g),'repeat',rep,'seed',seed,'initialID',initialID,'DDQN_loss',env.loss,'hold_loss',held.loss, ...
            'DDQN_ids',env.selected,'hold_ids',held.selected,'snr',env.snr,'per',env.per,'draws',env.draws,'geometry',G,'config',C);
        save(fullfile(target,'paired_trace.mat'),'sample','-v7.3');
        writetable(runs,fullfile(out,'episode_runs.csv'));writetable(pairs,fullfile(out,'switch_pairs.csv'));
        fprintf('%s %d/10 | DDQN %.3f%% vs hold %.3f%% | switch probes %d\n',grids(g),rep,RM.packetLossRatio,HM.packetLossRatio,height(pairs));drawnow;
    end
    assert(agent.updateCount==updates&&isequal(agent.onlineNetwork.Learnables,originalWeights));
end
summary=table();metrics={'loss_pct','meanLength_ge2','burstCount_ge2','maxLength','onTime_pct','handovers'};
for grid=grids
    for mode=["DDQN","hold_initial"]
        T=runs(runs.grid==grid & runs.policy==mode,:);
        for j=1:numel(metrics)
            v=T.(metrics{j});summary=[summary;table(grid,mode,string(metrics{j}),mean(v),std(v), ...
                'VariableNames',{'grid','policy','metric','mean','std'})]; %#ok<AGROW>
        end
    end
end
localSummary=table();
for grid=grids
    T=pairs(pairs.grid==grid,:);delta=T.hold_peak_10s-T.DDQN_peak_10s;
    localSummary=[localSummary;table(grid,height(T),mean(T.DDQN_peak_10s),mean(T.hold_peak_10s),sum(delta>0),sum(delta==0),sum(delta<0), ...
        mean(T.DDQN_loss_10s),mean(T.hold_loss_10s),mean(T.hold_loss_1s-T.DDQN_loss_1s), ...
        sum(T.hold_peak_10s>=12&T.DDQN_peak_10s<12),sum(T.hold_peak_10s<12&T.DDQN_peak_10s>=12), ...
        'VariableNames',{'grid','switchProbes','DDQN_meanPeak_10s','hold_meanPeak_10s','DDQN_shorter','equalPeak','DDQN_longer', ...
        'DDQN_meanLoss_10s','hold_meanLoss_10s','holdMinusDDQN_loss_1s','DDQN_averted_ge12','DDQN_created_ge12'})]; %#ok<AGROW>
end
writetable(summary,fullfile(out,'episode_summary.csv'));writetable(localSummary,fullfile(out,'switch_summary.csv'));
R=struct('outputDir',out,'runs',runs,'summary',summary,'pairs',pairs,'localSummary',localSummary,'windowSeconds',windowSeconds);
save(fullfile(out,'diagnostic.mat'),'R','-v7.3');save(fullfile(out,'branch_windows.mat'),'windows','-v7.3');
fid=fopen(fullfile(out,'VERIFICATION.txt'),'w');fprintf(fid,'PASS: 30 frozen DDQN replays match original packet losses and selected IDs; shared SNR/PER/draws; forced-hold full packet reference checks; independent forks; no learning.\n');fclose(fid);
end
function id=choice(agent,env,margin)
S=env.observe();q=agent.values(S);[~,j]=max(q);old=find(S.features(4,:)>0,1);
if ~isempty(old)&&q(j)<q(old)+margin,j=old;end
id=S.ids(j);
end
function [peak,continues]=windowPeak(lost,streak)
peak=0;
for j=1:numel(lost)
    if lost(j),streak=streak+1;peak=max(peak,streak);else,streak=0;end
end
continues=lost(end);
end
function row=metricRow(grid,policy,rep,seed,M,lost,handovers)
edges=diff([false;lost;false]);lengths=find(edges==-1)-find(edges==1);multi=lengths(lengths>=2);
average=NaN;if ~isempty(multi),average=mean(multi);end
row=table(grid,policy,rep,seed,M.packetLossRatio,average,numel(multi),M.maxConsecutiveLoss,M.onTimeDeliveryRate_pct,handovers, ...
    'VariableNames',{'grid','policy','repeat','seed','loss_pct','meanLength_ge2','burstCount_ge2','maxLength','onTime_pct','handovers'});
end
