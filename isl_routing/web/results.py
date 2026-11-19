# 결과 분석 화면(results.html)용 데이터 - 저장된 학습 기록과 최종 평가 기록을 읽어 화면에 보낼 모양으로 만듦
#
# 학습 기록: 홈 폴더 rl_models (환경 변수 RL_SAVE_ROOT로 바꿀 수 있음)
#   묶음 = rl_models 아래 폴더 하나. 그 안의 routeC_*_s시드 폴더마다 eval_log.csv(검증), train_log.csv(학습 중)
#   (eval_log.csv가 바로 들어 있는 폴더는 학습 시드 하나짜리 묶음으로 봄)
# 평가 기록: 홈 폴더 isl_saved_runs 아래 per_seed.csv, summary.csv가 있는 폴더 (eval_routes.py가 만듦)
#
# 숫자 기준
#   학습 곡선: eval_log.csv의 검증 도착률 = 흐름 전체 (train_rl.validate가 흐름별로 나누지 않음)
#   최종 평가: 도착률, 최대 연속 손실은 흐름 0 (per_seed.csv의 mainOnTimeRate, mainMaxConsecLoss)
#             1분당 연속 손실, 95번째 백분위 길이, 평균 지연, 에피소드 비교는 흐름 전체 (compare_runs.py와 같은 값)
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing

from analysis.compare_runs import cut, mean_ci

LEVELS = ['base', 'high', 'severe']


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


def list_runs():
    # 학습 묶음과 평가 폴더 목록 (최근 것이 위)
    train = []
    root = train_root()
    if os.path.isdir(root):
        for name in os.listdir(root):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            if os.path.exists(os.path.join(d, 'eval_log.csv')):
                seeds = [name]
                base = root
            else:
                seeds = sorted(s for s in os.listdir(d) if os.path.exists(os.path.join(d, s, 'eval_log.csv')))
                base = d
            if seeds:
                t = max(os.path.getmtime(os.path.join(base, s, 'eval_log.csv')) for s in seeds)
                train.append(dict(name=name, seeds=seeds, time=t))
    ev = []
    root = eval_root()
    if os.path.isdir(root):
        for dirpath, dirs, files in os.walk(root):
            if dirpath[len(root):].count(os.sep) > 2:
                dirs[:] = []
                continue
            if 'per_seed.csv' in files and 'summary.csv' in files:
                rel = os.path.relpath(dirpath, root).replace(os.sep, '/')
                ev.append(dict(name=rel, time=os.path.getmtime(os.path.join(dirpath, 'per_seed.csv'))))
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
    d = _safe(root, name)
    seedDirs = [d] if os.path.exists(os.path.join(d, 'eval_log.csv')) else \
        sorted(os.path.join(d, s) for s in os.listdir(d) if os.path.exists(os.path.join(d, s, 'eval_log.csv')))
    seeds = []
    for sd in seedDirs:
        ev = read_csv(os.path.join(sd, 'eval_log.csv'))
        curves = {}
        for r in ev:
            curves.setdefault(r['level'], []).append(dict(episode=int(r['episode']), onTimeRate=_num(r['onTimeRate']),
                                                          burstPerMin=_num(r.get('burstPerMin')), decisions=_num(r.get('decisions'))))
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
    out = dict(name=name, flowZero=hasMain, levels={})
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
        out['levels'][lv] = dict(
            nSeeds=len(seeds), nModels=len(Cs),
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
                          bMax=float(bSeed[s][mx0]), cMax=mean([float(r[mx0]) for r in cBy[s]])) for s in seeds if cBy[s]])
    return out
