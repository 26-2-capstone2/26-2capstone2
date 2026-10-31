# 여러 세트 한 번에 실행 - main_isl.py를 시작 시드만 바꿔 여러 번 돌림 (학습 데이터 모으기용)
#
# 사용법: python run_batch.py 혼잡단계 라우팅 첫시작시드 세트수 [동시실행수]
#   혼잡단계: base, high, severe, 또는 all (세 단계를 모두 돌림)
#   예) python run_batch.py high routeB 1001 5
#       -> 시작 시드 1001, 1021, 1041, 1061, 1081 (세트마다 에피소드 20개 = 시드 20개, 총 시드 100개)
#   예) python run_batch.py high routeB 1001 5 3   -> 3개씩 동시에 실행 (CPU 코어가 넉넉할 때)
#   예) python run_batch.py all routeB 1001 5      -> base, high, severe 각각 5세트 (모두 같은 시드)
# 결과: 세트마다 홈 폴더 isl_saved_runs\라우팅_혼잡단계_날짜 에 저장 (같은 날 두 번째 세트부터 _2, _3이 붙음, 시드는 run_info.txt)
# 진행 기록: isl_saved_runs\batch_logs\ 에 세트별 터미널 출력 저장
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from config_isl import BG_LEVELS, config_isl

if len(sys.argv) < 5:
    sys.exit('사용법: python run_batch.py 혼잡단계 라우팅 첫시작시드 세트수 [동시실행수]')
levelArg, route, firstSeed, numSets = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
workers = int(sys.argv[5]) if len(sys.argv) > 5 else 1
levels = list(BG_LEVELS) if levelArg == 'all' else [levelArg]
for lv in levels:
    if lv not in BG_LEVELS:
        sys.exit(f'혼잡 단계는 {list(BG_LEVELS)} 또는 all: {lv}')

numEp = int(config_isl().numEpisodes)
seeds = [firstSeed + i * numEp for i in range(numSets)]   # 세트끼리 시드가 겹치지 않게 에피소드 수만큼 건너뜀
baseDir = os.path.dirname(os.path.abspath(__file__))
saveRoot = os.environ.get('ISL_SAVE_ROOT', os.path.join(os.path.expanduser('~'), 'isl_saved_runs'))
logDir = os.path.join(saveRoot, 'batch_logs')
os.makedirs(logDir, exist_ok=True)
jobs = [(lv, sd) for lv in levels for sd in seeds]
print(f'[배치] {route}, 혼잡 {levels}, 시작 시드 {seeds} ({len(jobs)}개 실행, 세트마다 시드 {numEp}개), 동시 {workers}개')


def run_one(job):
    lv, seed = job
    name = f'{route}_{lv}_seed{seed}'
    env = dict(os.environ, ISL_RESULTS_DIR=os.path.join(baseDir, 'results_batch', name))   # 동시 실행끼리 results 폴더가 섞이지 않게
    tic = time.time()
    with open(os.path.join(logDir, f'{name}.log'), 'w', encoding='utf-8') as log:
        code = subprocess.call([sys.executable, os.path.join(baseDir, 'main_isl.py'), str(seed), lv, route],
                               cwd=baseDir, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f'  {name}: {"완료" if code == 0 else "실패 (로그 확인)"} ({(time.time() - tic) / 60:.1f}분)', flush=True)
    return code


with ThreadPoolExecutor(max_workers=workers) as pool:
    codes = list(pool.map(run_one, jobs))
print(f'[배치 끝] 성공 {codes.count(0)} / {len(codes)}, 로그: {logDir}')
