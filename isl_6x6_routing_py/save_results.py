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

    numCopied = copy_files(codeDir, ['*.py'], codeOut) \
        + copy_files(resultDir, ['*.png', '*.gif', '*.csv'], resultOut)

    print(f'결과 저장 완료: {saveDir} ({numCopied}개 파일)')


def copy_files(srcDir, patterns, dstDir):
    n = 0
    for pattern in patterns:
        for f in sorted(glob.glob(os.path.join(srcDir, pattern))):
            shutil.copyfile(f, os.path.join(dstDir, os.path.basename(f)))
            n += 1
    return n
