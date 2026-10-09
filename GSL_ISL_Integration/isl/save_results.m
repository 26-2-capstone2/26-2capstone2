% 결과 백업 - 코드(.m)와 결과(이미지, CSV)를 지정한 폴더로 복사 (1. main_isl 마지막에 자동 실행)
%
function save_results(codeDir, resultDir, saveDir)
% codeDir: .m 파일이 있는 폴더, resultDir: results 폴더, saveDir: 저장할 폴더
% 저장 구조: saveDir\code\*.m, saveDir\results\*.png, *.gif, *.csv
% 같은 이름의 파일은 덮어씀

codeOut = fullfile(saveDir, 'code');
resultOut = fullfile(saveDir, 'results');
if ~exist(codeOut, 'dir'), mkdir(codeOut); end
if ~exist(resultOut, 'dir'), mkdir(resultOut); end

numCopied = copy_files(codeDir, {'*.m'}, codeOut) ...
    + copy_files(resultDir, {'*.png', '*.gif', '*.csv'}, resultOut);

fprintf('결과 저장 완료: %s (%d개 파일)\n', saveDir, numCopied);
end

function n = copy_files(srcDir, patterns, dstDir)
n = 0;
for i = 1:numel(patterns)
    files = dir(fullfile(srcDir, patterns{i}));
    for j = 1:numel(files)
        copyfile(fullfile(srcDir, files(j).name), fullfile(dstDir, files(j).name));
        n = n + 1;
    end
end
end
