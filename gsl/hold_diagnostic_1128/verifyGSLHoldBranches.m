function verifyGSLHoldBranches(out)
S=load(fullfile(out,'diagnostic.mat'),'R');R=S.R;W=load(fullfile(out,'branch_windows.mat'),'windows');W=W.windows;
assert(height(R.runs)==60&&height(R.pairs)==numel(W));checked=0;
grids=unique(R.pairs.grid,'stable').';
for grid=grids
    for rep=1:10
        E=load(fullfile(out,grid,sprintf('repeat_%02d',rep),'paired_trace.mat'),'sample');E=E.sample;
        rows=find(R.pairs.grid==grid&R.pairs.repeat==rep);
        for k=rows.'
            T=R.pairs(k,:);t=T.time_s;prior=0;
            for j=t*60:-1:1
                if ~E.DDQN_loss(j),break;end
                prior=prior+1;
            end
            assert(prior==T.priorStreak&&prior==W(k).priorStreak);
            assert(W(k).holdIDs(1)==T.currentID&&W(k).actualIDs(1)==T.DDQN_ID);
            for arm=1:2
                if arm==1,ids=W(k).actualIDs;expected=W(k).actualLoss;else,ids=W(k).holdIDs;expected=W(k).holdLoss;end
                lost=false(600,1);old=T.currentID;ho=0;
                for second=1:10
                    id=ids(second);switching=id~=old;ho=ho+switching;
                    ii=(t+second-1)*60+(1:60).';u=(0:59).'/60;
                    local=(second-1)*60+(1:60).';
                    blocked=switching & u<E.config.handoverInterruption_s-16*eps(max(1,t+second));
                    lost(local)=blocked|E.draws(ii)<E.per(t+second,id);old=id;
                end
                assert(isequal(lost,expected));peak=0;streak=prior;
                for j=1:600
                    if lost(j),streak=streak+1;peak=max(peak,streak);else,streak=0;end
                end
                if arm==1
                    assert(sum(lost)==T.DDQN_loss_10s&&peak==T.DDQN_peak_10s&&ho==T.DDQN_HO_10s);
                    assert(isequal(lost,E.DDQN_loss(t*60+(1:600))));
                else
                    assert(sum(lost)==T.hold_loss_10s&&peak==T.hold_peak_10s&&ho==T.hold_HO_10s);
                end
                checked=checked+600;
            end
        end
    end
end
fid=fopen(fullfile(out,'BRANCH_VERIFICATION.txt'),'w');
fprintf(fid,'PASS: %d fork pairs; %d independently reconstructed packet outcomes; exact original-state streak, shared PER/draws, handover interruption, chosen IDs and window metrics.\n',height(R.pairs),checked);fclose(fid);
fprintf('BRANCH AUDIT PASS: %d pairs, %d packet outcomes\n',height(R.pairs),checked);
end
