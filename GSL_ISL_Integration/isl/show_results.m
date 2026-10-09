% 결과 보기 - 저장된 지표 표, 그래프, 애니메이션을 MATLAB 창에 띄움 (2. main_isl 다음에 실행)
%
% 저장된 결과를 MATLAB 창에 띄우기
% 1) 지표 요약 표 (명령 창), 2) 지표 그래프, 3) 애니메이션 재생 (반복)

baseDir = fileparts(mfilename('fullpath'));
outDir = fullfile(baseDir, 'results');

T = readtable(fullfile(outDir, 'metrics_summary.csv'));
disp(T);

f1 = figure('Name', '성능 지표 비교', 'NumberTitle', 'off', 'Color', 'w');
imshow(imread(fullfile(outDir, 'metrics_summary.png')), 'Border', 'tight');

if exist(fullfile(outDir, 'run_analysis.png'), 'file')
    f3 = figure('Name', '실행 분석', 'NumberTitle', 'off', 'Color', 'w');
    imshow(imread(fullfile(outDir, 'run_analysis.png')), 'Border', 'tight');
end

gifs = dir(fullfile(outDir, 'anim_*.gif'));
for i = 1:numel(gifs)
    [A, map] = imread(fullfile(outDir, gifs(i).name), 'Frames', 'all');
    f2 = figure('Name', ['애니메이션: ' gifs(i).name], 'NumberTitle', 'off', 'Color', 'w');
    h = imshow(A(:, :, :, 1), map, 'Border', 'tight');
    % 창을 닫을 때까지 반복 재생
    while isvalid(f2)
        for k = 1:size(A, 4)
            if ~isvalid(f2), break; end
            h.CData = A(:, :, :, k);
            pause(0.08);
        end
    end
end
