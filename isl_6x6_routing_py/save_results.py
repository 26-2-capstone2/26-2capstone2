# 결과 백업 - 코드(.py)와 결과(이미지, CSV)를 지정한 폴더로 복사 (main_isl, run_experiments 마지막에 자동 실행)
#
# 저장 폴더 구조 (SAVE_ROOT 아래)
#   routeA / routeB / routeC          <- 라우팅 알고리즘 (P.routeName)
#     baseline / train / evaluation   <- 시드 종류 (config_bg.py: 학습용 시드 -> train, 평가용 시드 -> evaluation, 그 외 -> baseline)
#       routeB_mid_102                <- 라우팅알고리즘_부하단계_시드 (실행 1개)
#         code\*.py, results\*.png, *.gif, *.csv, *.txt
#       routeB_summary_low-mid-high   <- run_experiments.py 여러 시드 요약 (평균 ± 편차)
# 예) route_B, 중간(mid), 시드 102  -> baseline_py\routeB\evaluation\routeB_mid_102
#     route_B, 매우 높음, 시드 5    -> baseline_py\routeB\train\routeB_extreme_5
#     route_B, 낮음, 기본 시드 1001 -> baseline_py\routeB\baseline\routeB_low_1001
# 같은 이름으로 다시 돌리면 같은 이름의 파일은 덮어씀
import glob
import os
import shutil

SAVE_ROOT = r'C:\Users\eun\Desktop\capstone_isl\baseline_py'   # 결과 저장 최상위 폴더 (본인 PC 경로로 변경)


def seed_group(seed, B):
    # 시드 종류: 평가용 -> evaluation, 학습용 -> train, 그 외(기본 1001 등) -> baseline
    if seed in B.evalSeeds:
        return 'evaluation'
    if seed in B.trainSeeds:
        return 'train'
    return 'baseline'


def run_name(routeName, level, seed):
    # 라우팅알고리즘_부하단계_시드  예) routeB_mid_102
    return f'{routeName}_{level}_{seed}'


def run_dir(routeName, level, seed, B):
    # 실행 1개의 저장 폴더  예) SAVE_ROOT\routeB\evaluation\routeB_mid_102
    return os.path.join(SAVE_ROOT, routeName, seed_group(seed, B), run_name(routeName, level, seed))


def summary_dir(routeName, group, levels):
    # 여러 시드 요약 저장 폴더  예) SAVE_ROOT\routeB\evaluation\routeB_summary_low-mid-high
    return os.path.join(SAVE_ROOT, routeName, group, f'{routeName}_summary_{"-".join(levels)}')


def save_results(codeDir, resultDir, saveDir, quiet=False):
    # codeDir: .py 파일이 있는 폴더, resultDir: results 폴더, saveDir: 저장할 폴더
    # 저장 구조: saveDir\code\*.py, saveDir\results\*.png, *.gif, *.csv, *.txt
    # 같은 이름의 파일은 덮어씀
    codeOut = os.path.join(saveDir, 'code')
    resultOut = os.path.join(saveDir, 'results')
    os.makedirs(codeOut, exist_ok=True)
    os.makedirs(resultOut, exist_ok=True)

    numCopied = copy_files(codeDir, ['*.py'], codeOut)
    if os.path.abspath(resultDir) != os.path.abspath(resultOut):   # 결과를 이미 그 자리에 쓴 경우는 복사 생략
        numCopied += copy_files(resultDir, ['*.png', '*.gif', '*.csv', '*.txt'], resultOut)

    if not quiet:
        print(f'결과 저장 완료: {saveDir} ({numCopied}개 파일)')


def copy_files(srcDir, patterns, dstDir):
    n = 0
    for pattern in patterns:
        for f in sorted(glob.glob(os.path.join(srcDir, pattern))):
            shutil.copyfile(f, os.path.join(dstDir, os.path.basename(f)))
            n += 1
    return n
