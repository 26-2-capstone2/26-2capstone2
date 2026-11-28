function verify_saved_experiment()
gsl=setupGSLNStep();here=fileparts(mfilename('fullpath'));
original=load(fullfile(gsl,'ddqn_6x11/results_ddqn_6x11/20261123_160855_135/agent.mat'),'checkpoint');
b=fullfile(here,'results_n1');p=fullfile(b,strtrim(fileread(fullfile(b,'latest_result.txt'))));fresh=load(fullfile(p,'agent.mat'),'checkpoint');
assert(original.checkpoint.updateCount==fresh.checkpoint.updateCount);
for j=1:height(original.checkpoint.onlineNetwork.Learnables)
    assert(isequal(extractdata(original.checkpoint.onlineNetwork.Learnables.Value{j}),extractdata(fresh.checkpoint.onlineNetwork.Learnables.Value{j})),'NSTEP:OriginalWeightsChanged');
end
folders=cell(7,1);
for j=1:4,folders{j}=fullfile(here,'results_hysteresis');end
for k=1:3
    n=[1 3 5];b=fullfile(here,sprintf('results_n%d',n(k)));folders{4+k}=fullfile(b,strtrim(fileread(fullfile(b,'latest_result.txt'))));
end
for repeat=1:10
    S=load(fullfile(folders{1},sprintf('h000_repeat_%02d',repeat),'preview.mat'),'preview');reference=S.preview;
    for k=2:7
        if k<=4,h=[0 10 30 50];folder=fullfile(folders{k},sprintf('h%03d_repeat_%02d',h(k),repeat));
        else,folder=fullfile(folders{k},sprintf('repeat_%02d',repeat));end
        S=load(fullfile(folder,'preview.mat'),'preview');p=S.preview;
        assert(isequal(reference.snr,p.snr)&&isequal(reference.P.phyRandomDraw,p.P.phyRandomDraw));
        assert(isequal(reference.P.generationTime_s,p.P.generationTime_s));
    end
end
fprintf('SAVED PHYSICS PAIRING PASS: all 70 runs share candidate SNR and packet draws by seed; n=1 final weights exactly reproduce original 100-episode model.\n');
end
