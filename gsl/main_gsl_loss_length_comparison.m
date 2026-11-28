function R=main_gsl_loss_length_comparison(mode)
% Default opens saved metrics. 'run' re-reads local raw loss logs; no training.
if nargin<1,mode='show';end
assert(any(strcmpi(mode,{'show','run'})));
root=fileparts(mfilename('fullpath'));out=fullfile(root,'연속손실길이_비교');
if ~isfolder(out),mkdir(out);end
grids=["6x11","20x20","36x36"];
policies=["MaxSNR_0dB","Elevation_4deg","quadratic_Q0.02"];
names=["최고 SNR","최고 고도각","DDQN"];runs=table();
if strcmpi(mode,'show')&&isfile(fullfile(out,'comparison.mat'))
    saved=load(fullfile(out,'comparison.mat'),'R');runs=saved.R.runs;
else
for g=1:3
    resultsRoot=fullfile(root,grids(g),'gsl','static_reward_1128','results_policy_comparison');
    pointer=strtrim(fileread(fullfile(resultsRoot,'latest_result.txt')));[~,name]=fileparts(pointer);
    folder=fullfile(resultsRoot,name);original=readtable(fullfile(folder,'runs.csv'),'TextType','string');
    for p=1:3
        for repeat=1:10
            T=readtable(fullfile(folder,policies(p),sprintf('repeat_%02d',repeat),'loss_runs.csv'));
            lengths=T.length_packets;multi=lengths(lengths>=2);
            check=original(original.policy==policies(p)&original.repeat==repeat,:);
            assert(sum(lengths)==check.lost&&max(lengths)==check.maxLossRun);
            average=NaN;if ~isempty(multi),average=mean(multi);end
            runs=[runs;table(grids(g),policies(p),repeat,average,numel(multi),max(lengths), ...
                'VariableNames',{'grid','policy','repeat','meanLength_ge2','burstCount_ge2','maxLength'})]; %#ok<AGROW>
        end
    end
end
end
summary=table();averages=zeros(3,3);deviations=averages;maximums=averages;maximumSD=averages;
for g=1:3
    for p=1:3
        T=runs(runs.grid==grids(g)&runs.policy==policies(p),:);
        averages(g,p)=mean(T.meanLength_ge2,'omitnan');deviations(g,p)=std(T.meanLength_ge2,'omitnan');
        maximums(g,p)=mean(T.maxLength);maximumSD(g,p)=std(T.maxLength);
        summary=[summary;table(grids(g),policies(p),averages(g,p),deviations(g,p),mean(T.burstCount_ge2),maximums(g,p), ...
            'VariableNames',{'grid','policy','meanLength_ge2','stdAcrossTrials','meanBurstCount_ge2','meanMaxLength'})]; %#ok<AGROW>
    end
end
writetable(runs,fullfile(out,'per_repeat.csv'));writetable(summary,fullfile(out,'summary.csv'));
f=figure('Name','평균과 최대 연속 손실 길이 비교','Color','w','Position',[60 60 1400 650]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile;drawBars(averages(:,[1 3]),deviations(:,[1 3]),grids,names([1 3]));
title('평균 연속 손실 길이 — 2개 이상 구간','FontName','Malgun Gothic');ylabel('패킷 수','FontName','Malgun Gothic');
nexttile;drawBars(maximums(:,[1 3]),maximumSD(:,[1 3]),grids,names([1 3]));
title('최대 연속 손실 길이 — 실행별 최댓값','FontName','Malgun Gothic');ylabel('패킷 수','FontName','Malgun Gothic');
sgtitle({'정적 위성군 · 감쇠 6 dB · 최고 SNR과 DDQN 비교', ...
    '각 회차에서 계산한 길이를 10회 평균 / 검은 선: 회차 간 표준편차 (신뢰구간 아님)'},'FontName','Malgun Gothic');
exportgraphics(f,fullfile(out,'mean_vs_max_length.png'),'Resolution',170);savefig(f,fullfile(out,'mean_vs_max_length.fig'));
f2=figure('Name','세 방식의 평균 연속 손실 길이','Color','w','Position',[100 100 1000 650]);
drawBars(averages,deviations,grids,names);title('평균 연속 손실 길이 — 2개 이상 구간, 10회 평가','FontName','Malgun Gothic');
ylabel('패킷 수','FontName','Malgun Gothic');
exportgraphics(f2,fullfile(out,'all_policies_mean_length.png'),'Resolution',170);savefig(f2,fullfile(out,'all_policies_mean_length.fig'));
R=struct('runs',runs,'summary',summary,'outputDir',out);save(fullfile(out,'comparison.mat'),'R');
fid=fopen(fullfile(out,'지표설명.txt'),'w','n','UTF-8');
fprintf(fid,'평균 길이: 각 실행에서 2개 이상 연속 손실된 구간만 골라 길이를 평균한 뒤 10회 평균.\n');
fprintf(fid,'최대 길이: 각 실행에서 가장 긴 손실 구간을 골라 10회 평균.\n검은 선은 10회 간 표본 표준편차이며 신뢰구간이 아니다.\n');
fprintf(fid,'기존 정적 간격 유지 실험의 90개 loss_runs.csv를 읽어 계산함. 3600km 공통 영역의 실험 결과가 아님.\n');fclose(fid);
assert(height(runs)==90);disp(summary);fprintf('90-run loss-length summary opened. Graphs: %s\n',out);
end
function drawBars(values,spread,grids,names)
b=bar(values);hold on;colors=[.20 .43 .72;.55 .55 .55;.90 .40 .13];
for k=1:size(values,2)
    colorIndex=k;if names(k)=="DDQN",colorIndex=3;elseif names(k)=="최고 고도각",colorIndex=2;end
    b(k).FaceColor=colors(colorIndex,:);
    errorbar(b(k).XEndPoints,values(:,k).',spread(:,k).','.k','LineWidth',1);
    for g=1:size(values,1)
        text(b(k).XEndPoints(g),values(g,k)+spread(g,k)+.025*max(values+spread,[],'all'),sprintf('%.2f',values(g,k)), ...
            'HorizontalAlignment','center','FontSize',10);
    end
end
ylim([0 1.2*max(values+spread,[],'all')]);xticks(1:3);xticklabels(grids);grid on;
set(gca,'FontName','Malgun Gothic','FontSize',11);legend(names,'Location','best','FontName','Malgun Gothic');
end
