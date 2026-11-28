function T=probe_saved_stability()
gsl=setupGSLStability();here=fileparts(mfilename('fullpath'));D=load(fullfile(gsl,'checkpoint_audit_1127/results/reference_states.mat'),'referenceStates');S=D.referenceStates{2,2};
modes={'control','low_lr','large_buffer','soft_target'};T=table();candidates=table();
for k=1:4
    for e=[100 200]
        if k==1,p=fullfile(gsl,'ddqn_1000/results_ddqn_1000/20261125_184805_356',sprintf('agent_episode_%04d.mat',e));
        else,p=fullfile(here,['results_' modes{k}],sprintf('agent_episode_%04d.mat',e));end
        D=load(p,'checkpoint');A=GSLTrendDoubleDQN(D.checkpoint.options);A.restore(D.checkpoint);q=A.values(S);
        [~,raw]=max(q);old=find(S.ids==44);ix=raw;if q(ix)<q(old)+.02,ix=old;end
        per=1-double(S.features(6,:));
        target=reshape(extractdata(predict(D.checkpoint.targetNetwork,dlarray(S.features,'CB'))),1,[]);
        row=table(string(modes{k}),e,S.ids(ix),S.ids(raw),per(ix),q(ix),q(old),q(raw)-q(old),mean(abs(q-target)), ...
            'VariableNames',{'mode','episode','selectedSatID','rawBestSatID','selectedPER','Qselected','Qstay44','bestQMinusStay44','onlineTargetGap'});
        T=[T;row]; %#ok<AGROW>
        tab=table(repmat(string(modes{k}),numel(S.ids),1),repmat(e,numel(S.ids),1),S.ids,q.',target.',per.', ...
            'VariableNames',{'mode','episode','satelliteID','onlineQ','targetQ','PER'});candidates=[candidates;tab]; %#ok<AGROW>
    end
end
writetable(T,fullfile(here,'fixed_probe_summary.csv'));writetable(candidates,fullfile(here,'fixed_probe_candidates.csv'));disp(T);
end
