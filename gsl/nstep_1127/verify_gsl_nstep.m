function verify_gsl_nstep()
setupGSLNStep();g=.95;S=struct('ids',1,'features',zeros(11,1,'single'));
make=@(r,d,greedy)struct('S',S,'index',1,'reward',r,'next',S,'done',d,'greedy',greedy);
q={};[q,a]=gslNStepAppend(q,make(1,false,true),3,g);assert(isempty(a));
[q,a]=gslNStepAppend(q,make(2,false,true),3,g);assert(isempty(a));
[q,a]=gslNStepAppend(q,make(3,false,true),3,g);
assert(numel(a)==1&&a{1}.horizon==3&&abs(a{1}.reward-(1+g*2+g^2*3))<1e-12&&abs(a{1}.discount-g^3)<1e-12);
[q,a]=gslNStepAppend(q,make(4,true,true),3,g);assert(isempty(q)&&numel(a)==3);
assert(isequal(cellfun(@(v)v.horizon,a),[3 2 1])&&all(cellfun(@(v)v.done,a)));
q={};[q,~]=gslNStepAppend(q,make(1,false,true),3,g);[q,~]=gslNStepAppend(q,make(2,false,true),3,g);
[q,a]=gslNStepAppend(q,make(300,false,false),3,g);assert(a{1}.horizon==2&&a{1}.cut&&abs(a{1}.reward-(1+g*2))<1e-12&&~a{1}.done);
O=configGSLNStep(1);old=GSLTrendDoubleDQN(O);new=GSLNStepDoubleDQN(O);
root=setupGSLNStep();p=fullfile(root,'ddqn_6x11/results_ddqn_6x11/20261123_160855_135');
R=load(fullfile(p,'study.mat'),'R');C=configGSLToolboxPHY(R.R.config);D=load(fullfile(p,'geometry.mat'),'geometry');
env=GSLTrendEpisode(C,D.geometry,O,O.trainingSeeds(1));queue={};
for t=1:560
    S=env.observe();epsi=O.epsilonEnd+(O.epsilonStart-O.epsilonEnd)*max(0,1-(t-1)/O.epsilonDecaySteps);
    a=old.select(S,epsi,O.qHysteresis);b=new.select(S,epsi,O.qHysteresis);assert(a==b);
    [next,r,done]=env.step(S.ids(a));old.remember(S,a,r,next,done);
    item=struct('S',S,'index',a,'reward',r,'next',next,'done',done,'greedy',true);
    [queue,out]=gslNStepAppend(queue,item,1,g);v=out{1};new.remember(v.S,v.index,v.reward,v.next,v.done,v.discount);
    if mod(t,O.trainEvery)==0
        x=old.learn();y=new.learn();assert(isequaln(x,y));
        for j=1:height(old.onlineNetwork.Learnables)
            assert(isequal(extractdata(old.onlineNetwork.Learnables.Value{j}),extractdata(new.onlineNetwork.Learnables.Value{j})));
        end
    end
end
assert(isempty(queue));
fprintf('NSTEP PASS: discounted multi-step return, gamma^h, terminal flush, non-greedy cut, no episode leak; n=1 matches original actions/loss/weights through 560 steps.\n');
end
