# 최종 성능 목표 판정 - 학습 안정화 계획 9번 (B 대비 개선, 비열등성, 신뢰성, 이상 신호)
#
# 실행 (isl_routing 폴더에서):
#   python analysis/compare_runs.py 평가폴더
#   평가폴더 = eval_routes.py를 A, B, C(학습 시드별 모델 여러 개)로 돌린 결과 (summary.csv, per_seed.csv)
#   예) python eval_routes.py 모델0,모델1,모델2  ->  python analysis/compare_runs.py ~/isl_saved_runs/eval_날짜
#
# C 모델마다 B와 비교한 뒤, 학습 시드 여러 개의 평균과 95% 신뢰구간(t 분포)을 계산
# 저장: 평가폴더에 targets_report.md (판정표), targets_report.csv (C 모델별 값)
import csv
import os
import sys

import numpy as np

# 단계별 목표 (학습 안정화 계획 9번). 감소율은 B 대비 %
TARGETS = {
    'base':   dict(burstCut=10.0, p95Cut=0.0, onTimeMin=-1.0),
    'high':   dict(burstCut=20.0, p95Cut=15.0, onTimeMin=-1.0),
    'severe': dict(burstCut=20.0, p95Cut=20.0, onTimeMin=5.0),
    'extreme': dict(burstCut=20.0, p95Cut=20.0, onTimeMin=5.0),   # 테스트 6 최악 상황 (severe와 같은 기준)
}
LATENCY_MAX = 5.0       # 평균 지연 증가 B 대비 +5 ms 이내
WIN_RATE_MIN = 70.0     # 평가 시드 중 C의 연속 손실이 B보다 적은 비율 70% 이상
ANOMALY_CUT = 80.0      # 연속 손실 감소 80% 이상이면 이상 신호
ANOMALY_LOSS = 0.5      # C 손실률 0.5% 미만이면 이상 신호 (0%에 가까움)
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}   # t(0.975, 자유도)


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def cut(b, c):
    # B 대비 감소율 (%). B가 0이면 비교 불가
    return None if b == 0 else (b - c) / b * 100


def mean_ci(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, None
    m = float(np.mean(xs))
    if len(xs) < 2:
        return m, None, None
    h = T95.get(len(xs) - 1, 1.96) * float(np.std(xs, ddof=1)) / np.sqrt(len(xs))
    return m, m - h, m + h


def fmt(x, d=1):
    return '-' if x is None else f'{x:.{d}f}'


def main():
    if len(sys.argv) < 2:
        print('사용법: python analysis/compare_runs.py 평가폴더')
        return
    d = sys.argv[1]
    summ = read_csv(os.path.join(d, 'summary.csv'))
    seeds = read_csv(os.path.join(d, 'per_seed.csv'))
    levels = [lv for lv in ['base', 'high', 'severe', 'extreme'] if any(r['level'] == lv for r in summ)]

    lines = ['# 최종 성능 목표 판정 (B 대비)', '', f'평가 폴더: {d}', '',
             '감소율 = (B - C) / B. 학습 시드가 2개 이상이면 평균 [95% 신뢰구간]', '']
    table = []
    cOnTimeByLevel = {}
    for lv in levels:
        T = TARGETS[lv]
        B = next((r for r in summ if r['level'] == lv and r['route'] == 'routeB'), None)
        Cs = [r for r in summ if r['level'] == lv and r['route'] == 'routeC']
        if B is None or not Cs:
            lines += [f'## {lv}', '', 'B 또는 C 결과가 없어 판정하지 않음', '']
            continue
        bSeed = {r['seed']: r for r in seeds if r['level'] == lv and r['route'] == 'routeB'}
        per = []
        for c in Cs:
            cSeed = [r for r in seeds if r['level'] == lv and r['route'] == 'routeC' and r['cRun'] == c['cRun']]
            wins = sum(int(r['burstCount']) < int(bSeed[r['seed']]['burstCount']) for r in cSeed)
            ties = sum(int(r['burstCount']) == int(bSeed[r['seed']]['burstCount']) for r in cSeed)
            worstC = min(float(r['onTimeRate']) for r in cSeed)
            worstB = min(float(r['onTimeRate']) for r in bSeed.values())
            row = dict(level=lv, cRun=c['cRun'],
                       burstCut=cut(float(B['burstPerMin']), float(c['burstPerMin'])),
                       p95Cut=cut(float(B['burstLenP95']), float(c['burstLenP95'])),
                       onTimeDiff=float(c['onTimeRate']) - float(B['onTimeRate']),
                       latencyDiff=float(c['avgLatency_ms']) - float(B['avgLatency_ms']),
                       winRate=wins / len(cSeed) * 100, ties=ties, n=len(cSeed),
                       worstOk=worstC >= worstB, worstC=worstC, worstB=worstB,
                       cLoss=float(c['lossRate']), cOnTime=float(c['onTimeRate']))
            per.append(row)
            table.append(row)
        cOnTimeByLevel[lv] = np.mean([r['cOnTime'] for r in per])

        bc, bLo, bHi = mean_ci([r['burstCut'] for r in per])
        pc, _, _ = mean_ci([r['p95Cut'] for r in per])
        od, _, _ = mean_ci([r['onTimeDiff'] for r in per])
        ld, _, _ = mean_ci([r['latencyDiff'] for r in per])
        wr, _, _ = mean_ci([r['winRate'] for r in per])
        ok = lambda c: '만족' if c else '미달'
        ci = f' [{fmt(bLo)}, {fmt(bHi)}]' if bLo is not None else ''
        p95Goal = '증가하지 않음' if T['p95Cut'] == 0 else f'{T["p95Cut"]:.0f}% 이상 감소'
        onGoal = f'B보다 {abs(T["onTimeMin"]):.0f}%p 넘게 낮지 않음' if T['onTimeMin'] < 0 else f'B보다 {T["onTimeMin"]:.0f}%p 이상 높음'
        lines += [f'## {lv}', '',
                  f'- B: 도착률 {B["onTimeRate"]}%, 연속 손실 {B["burstPerMin"]}/분, 95번째 백분위 길이 {B["burstLenP95"]}, '
                  f'평균 지연 {B["avgLatency_ms"]} ms',
                  f'- C 모델 {len(per)}개, 평가 시드 {per[0]["n"]}개', '',
                  '| 목표 | 기준 | 결과 | 판정 |', '|---|---|---|---|',
                  f'| 1분당 연속 손실 감소 | {T["burstCut"]:.0f}% 이상 | {fmt(bc)}%{ci} | {ok(bc is not None and bc >= T["burstCut"])} |',
                  f'| 연속 손실 길이 95번째 백분위 | {p95Goal} | {fmt(pc)}% 감소 | {ok(pc is not None and pc >= T["p95Cut"])} |',
                  f'| 기한 내 도착률 | {onGoal} | {fmt(od, 2)}%p | {ok(od is not None and od >= T["onTimeMin"])} |',
                  f'| 평균 지연 | +{LATENCY_MAX:.0f} ms 이내 | {fmt(ld, 2)} ms | {ok(ld is not None and ld <= LATENCY_MAX)} |',
                  f'| 짝지은 승률 | {WIN_RATE_MIN:.0f}% 이상 | {fmt(wr)}% | {ok(wr is not None and wr >= WIN_RATE_MIN)} |',
                  f'| 신뢰구간 하한 > 0 | 학습 시드 2개 이상 | {fmt(bLo)} | '
                  f'{"판정 불가" if bLo is None else ok(bLo > 0)} |',
                  f'| 최악 에피소드 도착률 | B 이상 | C {min(r["worstC"] for r in per):.2f}%, B {per[0]["worstB"]:.2f}% | '
                  f'{ok(all(r["worstOk"] for r in per))} |', '']
        warn = []
        if bc is not None and bc >= ANOMALY_CUT:
            warn.append(f'연속 손실 감소 {bc:.1f}% (80% 이상)')
        if any(r['cLoss'] < ANOMALY_LOSS for r in per):
            warn.append('C 손실률이 0%에 가까움')
        if any(r['winRate'] == 100 for r in per):
            warn.append('모든 평가 시드에서 C가 이김')
        if warn:
            lines += ['이상 신호 (환경부터 점검): ' + ', '.join(warn), '']
        lines += ['C 모델별: ' + ', '.join(f'#{r["cRun"]} 감소 {fmt(r["burstCut"])}%, 승률 {fmt(r["winRate"])}% '
                                         f'(같음 {r["ties"]}개)' for r in per), '']
    if len(cOnTimeByLevel) == 3 and max(cOnTimeByLevel.values()) - min(cOnTimeByLevel.values()) < 1.0:
        lines += ['이상 신호: base, high, severe 사이 C의 도착률 차이가 1%p 미만 (환경 점검 필요)', '']

    text = '\n'.join(lines)
    print(text)
    with open(os.path.join(d, 'targets_report.md'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    if table:
        with open(os.path.join(d, 'targets_report.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(table[0]))
            w.writeheader()
            w.writerows(table)
    print(f'저장: {os.path.join(d, "targets_report.md")}')


if __name__ == '__main__':
    main()
