# 결과 분석 화면(results.html)용 데이터 - 저장된 학습 기록과 최종 평가 기록을 읽어 화면에 보낼 모양으로 만듦
#
# 학습 기록: 홈 폴더 rl_models (환경 변수 RL_SAVE_ROOT로 바꿀 수 있음)
#   묶음 = rl_models 아래 폴더 하나. 그 안의 routeC_*_s시드 폴더마다 eval_log.csv(검증), train_log.csv(학습 중)
#   rl_models 바로 아래 routeC_이름_s시드 폴더들(eval_log.csv가 바로 들어 있음)은 '_s시드'를 뗀 이름으로 한 묶음
#   망 구조(topo)는 폴더 이름에서 읽음: iridium, starlink20x20, starlink36x36, starlink, 없으면 grid (6 x 6 이전 기록)
# 평가 기록: 홈 폴더 isl_saved_runs 아래 per_seed.csv, summary.csv가 있는 폴더 (eval_routes.py가 만듦)
#
# 숫자 기준
#   학습 곡선: eval_log.csv의 검증 도착률 = 흐름 전체 (train_rl.validate가 흐름별로 나누지 않음)
#   최종 평가: 도착률, 최대 연속 손실은 흐름 0 (per_seed.csv의 mainOnTimeRate, mainMaxConsecLoss)
#             1분당 연속 손실, 95번째 백분위 길이, 평균 지연, 에피소드 비교는 흐름 전체 (compare_runs.py와 같은 값)
import csv
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing

from analysis.compare_runs import cut, mean_ci

LEVELS = ['base', 'high', 'severe']
SEED_DIR = re.compile(r'^(.+)_s(\d+)$')


def topo_of(name):
    m = re.search(r'(iridium|starlink\d+x\d+|starlink)', name)
    return m.group(1) if m else 'grid'


def _home(*p):
    return os.path.join(os.path.expanduser('~'), *p)


def train_root():
    return os.environ.get('RL_SAVE_ROOT', _home('rl_models'))


def eval_root():
    return _home('isl_saved_runs')


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _seed_dirs(root, name):
    # 묶음 이름 -> 학습 시드 폴더 목록 (하위 폴더 묶음, 또는 바로 아래 name_s시드 폴더들)
    d = os.path.join(root, name)
    if os.path.isdir(d) and not os.path.exists(os.path.join(d, 'eval_log.csv')):
        return sorted(os.path.join(d, s) for s in os.listdir(d) if os.path.exists(os.path.join(d, s, 'eval_log.csv')))
    out = [os.path.join(root, s) for s in os.listdir(root)
           if (s == name or (SEED_DIR.match(s) and SEED_DIR.match(s).group(1) == name)) and os.path.exists(os.path.join(root, s, 'eval_log.csv'))]
    return sorted(out, key=lambda x: int(SEED_DIR.match(os.path.basename(x)).group(2)) if SEED_DIR.match(os.path.basename(x)) else 0)


def list_runs():
    # 학습 묶음과 평가 폴더 목록 (최근 것이 위)
    train = {}
    root = train_root()
    if os.path.isdir(root):
        for name in os.listdir(root):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            if os.path.exists(os.path.join(d, 'eval_log.csv')):
                m = SEED_DIR.match(name)
                group = m.group(1) if m else name
                train.setdefault(group, []).append(os.path.join(d, 'eval_log.csv'))
            else:
                train.setdefault(name, []).extend(os.path.join(d, s, 'eval_log.csv') for s in os.listdir(d)
                                                  if os.path.exists(os.path.join(d, s, 'eval_log.csv')))
    # 망 구조는 묶음 이름에 없으면 시드 폴더 이름에서 읽음 (예 r6_noback_risk/routeC_iridium_..._s0)
    train = [dict(name=k, topo=topo_of(k + ' ' + os.path.basename(os.path.dirname(v[0]))), seeds=len(v), time=max(os.path.getmtime(f) for f in v)) for k, v in train.items() if v]
    ev = []
    root = eval_root()
    if os.path.isdir(root):
        for dirpath, dirs, files in os.walk(root):
            if dirpath[len(root):].count(os.sep) > 2:
                dirs[:] = []
                continue
            if 'per_seed.csv' in files and 'summary.csv' in files:
                rel = os.path.relpath(dirpath, root).replace(os.sep, '/')
                ev.append(dict(name=rel, topo=topo_of(rel), time=os.path.getmtime(os.path.join(dirpath, 'per_seed.csv'))))
    train.sort(key=lambda r: -r['time'])
    ev.sort(key=lambda r: -r['time'])
    return dict(train=train, eval=ev)


def _safe(root, rel):
    # 화면에서 온 이름이 저장 폴더 밖을 가리키지 않게
    p = os.path.realpath(os.path.join(root, rel))
    if not p.startswith(os.path.realpath(root) + os.sep):
        raise ValueError(f'잘못된 폴더 이름: {rel}')
    return p


def load_train(name):
    # 묶음 하나: 학습 시드마다 검증 곡선(단계별, 에피소드별)과 ε이 끝난 에피소드
    root = train_root()
    _safe(root, name)
    seedDirs = _seed_dirs(root, name)
    seeds = []
    for sd in seedDirs:
        ev = read_csv(os.path.join(sd, 'eval_log.csv'))
        curves = {}
        for r in ev:
            curves.setdefault(r['level'], []).append(dict(episode=int(r['episode']), onTimeRate=_num(r['onTimeRate']),
                                                          burstPerMin=_num(r.get('burstPerMin')), decisions=_num(r.get('decisions')),
                                                          maxConsec0=_num(r.get('mainMaxConsecLoss'))))   # 흐름 0 최대 연속 손실 (4차 이후 기록만)
        epsEnd, epsMin = None, None
        tp = os.path.join(sd, 'train_log.csv')
        if os.path.exists(tp):
            eps = [(int(r['episode']), _num(r['epsilon'])) for r in read_csv(tp) if _num(r.get('epsilon')) is not None]
            if eps:
                epsMin = min(e for _, e in eps)
                epsEnd = next((ep for ep, e in eps if e <= epsMin + 1e-6), None)
        label = os.path.basename(sd)
        seeds.append(dict(name=label, seed=label.rsplit('_s', 1)[-1] if '_s' in label else label,
                          levels=[lv for lv in LEVELS if lv in curves], curves=curves, epsEnd=epsEnd))
    return dict(name=name, seeds=seeds)


def load_eval(name):
    # 평가 폴더 하나: 단계마다 카드, 막대, 요약, 시드별 표
    d = _safe(eval_root(), name)
    summ = read_csv(os.path.join(d, 'summary.csv'))
    rows = read_csv(os.path.join(d, 'per_seed.csv'))
    hasMain = bool(rows) and 'mainOnTimeRate' in rows[0]
    on0 = 'mainOnTimeRate' if hasMain else 'onTimeRate'
    mx0 = 'mainMaxConsecLoss' if hasMain else 'maxConsecLoss'
    from config_isl import config_isl
    P = config_isl()
    perFlow = int(P.simTime * P.genRate / 1000)   # 흐름 하나가 에피소드에 보내는 패킷 수 (10초 x 초당 60 = 600)
    out = dict(name=name, flowZero=hasMain, perFlow=perFlow, levels={})
    for lv in LEVELS:
        B = next((r for r in summ if r['level'] == lv and r['route'] == 'routeB'), None)
        Cs = [r for r in summ if r['level'] == lv and r['route'] == 'routeC']
        bSeed = {r['seed']: r for r in rows if r['level'] == lv and r['route'] == 'routeB'}
        cRows = [r for r in rows if r['level'] == lv and r['route'] == 'routeC']
        if B is None or not Cs or not bSeed or not cRows:
            continue
        seeds = sorted(bSeed, key=lambda s: int(s))
        cBy = {s: [r for r in cRows if r['seed'] == s] for s in seeds}
        mean = lambda xs: float(np.mean(xs)) if len(xs) else None
        bOn = mean([float(bSeed[s][on0]) for s in seeds])
        cOn = mean([float(r[on0]) for r in cRows])
        bMx = mean([float(bSeed[s][mx0]) for s in seeds])
        cMx = mean([float(r[mx0]) for r in cRows])
        per = []
        for c in Cs:
            cs = [r for r in cRows if r['cRun'] == c['cRun']]
            wins = sum(int(r['burstCount']) < int(bSeed[r['seed']]['burstCount']) for r in cs)
            per.append(dict(burstCut=cut(float(B['burstPerMin']), float(c['burstPerMin'])),
                            p95Cut=cut(float(B['burstLenP95']), float(c['burstLenP95'])),
                            latencyDiff=float(c['avgLatency_ms']) - float(B['avgLatency_ms']),
                            winRate=wins / len(cs) * 100 if cs else None,
                            worstC=min(float(r['onTimeRate']) for r in cs) if cs else None))
        bc, bLo, bHi = mean_ci([p['burstCut'] for p in per])
        f = lambda r, k: _num(r.get(k))
        # 연속 손실 길이 분포 (흐름 전체, 평가 시드 전체 합): 3~4개, 5~9개, 10개 이상
        lens = lambda r: [int(r['burstCount']) - int(r['runs_ge5']), int(r['runs_ge5']) - int(r['runs_ge10']), int(r['runs_ge10'])]
        detail = dict(lenDist=[lens(B), [mean([lens(c)[i] for c in Cs]) for i in range(3)]],
                      share=[f(B, 'burstShareOfLoss'), mean([f(c, 'burstShareOfLoss') for c in Cs])],
                      avgLen=[f(B, 'avgBurstLen'), mean([f(c, 'avgBurstLen') for c in Cs])],
                      # 모델별 흐름 0 지표 (summary에 흐름 0 열이 있을 때만)
                      models=[dict(cRun=c['cRun'], burst0=f(c, 'mainBurstPerMin'), max0=f(c, 'mainMaxConsecLoss'), on0=f(c, 'mainOnTimeRate')) for c in Cs],
                      base0=dict(burst0=f(B, 'mainBurstPerMin'), max0=f(B, 'mainMaxConsecLoss'), on0=f(B, 'mainOnTimeRate')))
        out['levels'][lv] = dict(
            nSeeds=len(seeds), nModels=len(Cs), detail=detail,
            cards=dict(onTime=[bOn, cOn], maxConsec=[bMx, cMx],
                       burstPerMin=[float(B['burstPerMin']), mean([float(c['burstPerMin']) for c in Cs])],
                       burstLenP95=[float(B['burstLenP95']), mean([float(c['burstLenP95']) for c in Cs])],
                       latency=[float(B['avgLatency_ms']), mean([float(c['avgLatency_ms']) for c in Cs])]),
            summary=dict(burstCut=bc, burstCutLo=bLo, burstCutHi=bHi,
                         p95Cut=mean_ci([p['p95Cut'] for p in per])[0],
                         winRate=mean_ci([p['winRate'] for p in per])[0],
                         latencyDiff=mean_ci([p['latencyDiff'] for p in per])[0],
                         worstC=mean([p['worstC'] for p in per if p['worstC'] is not None]),
                         worstB=min(float(r['onTimeRate']) for r in bSeed.values())),
            perSeed=[dict(seed=int(s), bOn=float(bSeed[s][on0]), cOn=mean([float(r[on0]) for r in cBy[s]]),
                          bMax=float(bSeed[s][mx0]), cMax=mean([float(r[mx0]) for r in cBy[s]]),
                          bBurst0=f(bSeed[s], 'mainBurstPerMin'), cBurst0=mean([f(r, 'mainBurstPerMin') for r in cBy[s]]) if hasMain else None,
                          # 흐름 통째 손실: 어떤 흐름이든 한 에피소드 패킷을 전부 잃음 (최대 연속 손실 = 흐름당 패킷 수). RL(C)은 모델 몇 개에서
                          bWhole=int(float(bSeed[s]['maxConsecLoss']) >= perFlow),
                          cWhole=sum(float(r['maxConsecLoss']) >= perFlow for r in cBy[s]), nC=len(cBy[s])) for s in seeds if cBy[s]])
    return out
