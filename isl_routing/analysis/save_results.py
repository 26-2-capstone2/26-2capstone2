# 결과 백업 - 코드(.py)와 결과(이미지, CSV)를 지정한 폴더로 복사 (1. main_isl 마지막에 자동 실행)
#
import glob
import os
import shutil


def save_results(codeDir, resultDir, saveDir):
    # codeDir: .py 파일이 있는 폴더, resultDir: results 폴더, saveDir: 저장할 폴더
    # 저장 구조: saveDir\code\*.py, saveDir\results\*.png, *.gif, *.csv
    # 같은 이름의 파일은 덮어씀
    codeOut = os.path.join(saveDir, 'code')
    resultOut = os.path.join(saveDir, 'results')
    os.makedirs(codeOut, exist_ok=True)
    os.makedirs(resultOut, exist_ok=True)

    numCopied = copy_code(codeDir, codeOut) \
        + copy_files(resultDir, ['*.png', '*.gif', '*.csv', '*.txt'], resultOut)

    print(f'결과 저장 완료: {saveDir} ({numCopied}개 파일)')


def copy_code(codeDir, dstDir):
    # .py를 폴더 구조 그대로 복사 (routing, sim, analysis, viz, docs, rl 하위 폴더 포함)
    n = 0
    for f in sorted(glob.glob(os.path.join(codeDir, '**', '*.py'), recursive=True)):
        if '__pycache__' in f or 'results_batch' in f:
            continue
        out = os.path.join(dstDir, os.path.relpath(f, codeDir))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copyfile(f, out)
        n += 1
    return n


def copy_files(srcDir, patterns, dstDir):
    n = 0
    for pattern in patterns:
        for f in sorted(glob.glob(os.path.join(srcDir, pattern))):
            shutil.copyfile(f, os.path.join(dstDir, os.path.basename(f)))
            n += 1
    return n
