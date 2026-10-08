# 여러 시드 실험 - 배경 부하 단계 x 시드를 여러 번 돌려 지표를 평균 ± 편차로 정리 (설정과 on/off는 config_bg.py)
#
# 실행: python run_experiments.py   (부하 3단계 x 시드 10개 = 30번, 동시 6개면 약 30분)
#
# 평가 (config_bg.py B.runEval = True): ε = 0, 평가용 시드(101~)
# 학습 데이터 수집 (B.runTrain = True): ε = B.trainEpsilon, 학습용 시드(1~)
#
# 저장 위치 (최상위 경로와 폴더 규칙은 save_results.py)
#   실행 1개      : baseline_py\routeB\evaluation\routeB_mid_102\      (학습용 시드는 train 폴더)
#                     results\metrics_summary.csv, packet_log_*.csv, run_info.txt
#                     (학습 데이터면 decision_log_*.csv 추가), code\*.py
#   여러 시드 요약: baseline_py\routeB\evaluation\routeB_summary_low-mid-high\results\
#                     eval_runs.csv     : 실행 1번 = 1줄 (부하 단계, 시드, 지표 전부)
#                     eval_stats.csv    : 부하 단계 x 지표별 평균, 표준편차, 최소, 최대
#                     eval_summary.png  : 부하 단계별 지표 막대(평균) + 오차 막대(표준편차) + 시드별 점
#                     conditions.txt    : 이번 실험의 고정 조건 (기한, 용량, 큐, 배경 패턴, 시드 등)
#                   (학습 데이터 요약은 train\routeB_summary_..., 같은 요약이 results\experiments\ 에도 남음)
import csv
import os
import time
from datetime import datetime
from multiprocessing import Pool

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from compute_metrics import compute_metrics
from config_bg import apply_bg, config_bg
from config_isl import config_isl
from run_isl_sim import DECISION_LOG_COLUMNS, PACKET_LOG_COLUMNS, ROUTE_LABELS, packet_log_table, run_isl_sim, writetable
from save_results import run_dir, run_name, save_results, summary_dir
from viz_colors import use_korean_font, viz_colors

baseDir = os.path.dirname(os.path.abspath(__file__))
expDir = os.path.join(baseDir, 'results', 'experiments')   # 여러 시드 요약 (작업용 사본)
GROUP = {'eval': 'evaluation', 'train': 'train'}

# 정리할 지표: (이름, 표시 이름, 배율, 단위)
METRICS = [
    ('onTimeRate', '기한 내 도착률', 100, '%'),
    ('lossRate', '손실률', 100, '%'),
    ('avgLatency_ms', '평균 지연', 1, 'ms'),
    ('maxConsecLoss', '최대 연속 손실', 1, '개'),
    ('overflow', '큐 오버플로', 1, '개'),
    ('late', '기한 초과 (목적지+중간)', 1, '개'),
    ('routeChanges', '경로 변경 수', 1, '회'),
    ('avgHops', '평균 홉 수', 1, '홉'),
]


def one_run(job):
    # 실행 1번: (모드, 부하 단계, 시드) -> 지표 1줄. 시드는 배경 패턴과 ε 무작위 선택에 같이 사용
    mode, level, seed = job
    tic = time.time()
    B = config_bg()
    P = apply_bg(config_isl(), B, level, seed)
    P.nodeLogEnable = False   # 여러 번 돌리는 실험에서는 노드 기록 생략
    epsilon = 0 if mode == 'eval' else B.trainEpsilon
    R = run_isl_sim(P, P.genRate, epsilon, seed, False)
    M = compute_metrics(R, P)

    # 실행 1개 폴더: baseline_py\routeB\(evaluation / train)\routeB_단계_시드
    saveDir = run_dir(P.routeName, level, seed, B)
    resDir = os.path.join(saveDir, 'results')
    os.makedirs(resDir, exist_ok=True)
    tag = f'rate{P.genRate}pps_eps{epsilon:.1f}'
    writetable(packet_log_table(R), PACKET_LOG_COLUMNS, os.path.join(resDir, f'packet_log_{tag}.csv'), '%d')
    if mode == 'train':
        writetable(R.decisionLog, DECISION_LOG_COLUMNS, os.path.join(resDir, f'decision_log_{tag}.csv'), '%.15g')
    write_csv([vars(M)], os.path.join(resDir, 'metrics_summary.csv'))
    with open(os.path.join(resDir, 'run_info.txt'), 'w', encoding='utf-8') as f:
        f.write(f'실행 시각: {datetime.now():%Y-%m-%d %H:%M}\n라우팅: {P.routeName}\n'
                f'배경 부하: {level} (흐름별 {B.levels[level]} packets/step)\n시드: {seed}\nε: {epsilon}\n')
    save_results(baseDir, resDir, saveDir, quiet=True)   # 코드 복사

    row = {'mode': mode, 'name': run_name(P.routeName, level, seed),
           'level': level, 'bgRate': B.levels[level], 'seed': seed}
    row.update(vars(M))
    row['late'] = M.lateAtDst + M.lateMid
    row['runTime_s'] = round(time.time() - tic, 1)
    return row


def stats_rows(rows, levels):
    # 부하 단계 x 지표별 평균, 표준편차(표본), 최소, 최대
    out = []
    for level in levels:
        group = [r for r in rows if r['level'] == level]
        if not group:
            continue
        for key, name, scale, unit in METRICS:
            v = np.array([r[key] for r in group], dtype=float) * scale
            out.append({'level': level, 'metric': key, 'name': name, 'unit': unit, 'n': len(v),
                        'mean': v.mean(), 'std': v.std(ddof=1) if len(v) > 1 else 0.0,
                        'min': v.min(), 'max': v.max()})
    return out


def write_csv(rows, path):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:   # utf-8-sig: 엑셀에서 한글 안 깨짐
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def plot_summary(rows, levels, B, pngPath):
    # 부하 단계별 지표: 막대 = 평균, 오차 막대 = 표준편차, 점 = 시드 1개
    C = viz_colors()
    use_korean_font(C)
    fig, axs = plt.subplots(2, 4, figsize=(17, 8), constrained_layout=True, facecolor='w')
    x = np.arange(len(levels))
    rng = np.random.RandomState(0)   # 점 겹침 방지용 좌우 흔들기
    for ax, (key, name, scale, unit) in zip(axs.ravel(), METRICS):
        vals = [np.array([r[key] for r in rows if r['level'] == lv], dtype=float) * scale for lv in levels]
        mean = [v.mean() for v in vals]
        std = [v.std(ddof=1) if len(v) > 1 else 0 for v in vals]
        ax.bar(x, mean, color=C.series[0], alpha=0.35, width=0.6)
        ax.errorbar(x, mean, yerr=std, fmt='none', ecolor=C.text, capsize=6, linewidth=1.5)
        for i, v in enumerate(vals):
            ax.scatter(x[i] + rng.uniform(-0.15, 0.15, len(v)), v, s=14, color=C.series[0], zorder=3)
            ax.text(x[i], mean[i], f'{mean[i]:.1f}\n±{std[i]:.1f}', ha='center', va='bottom', fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([f'{B.levelNames[lv]}\n({B.levels[lv]})' for lv in levels])
        ax.set_title(f'{name} ({unit})')
        ax.grid(True, axis='y', color=C.grid)
    n = len([r for r in rows if r['level'] == levels[0]])
    fig.suptitle(f'배경 부하 단계별 성능 ({ROUTE_LABELS[rows[0]["routeName"]]}, ε = 0, 평가용 시드 {n}개, 막대 = 평균, 오차 = 표준편차)',
                 fontsize=14, color=C.text)
    fig.savefig(pngPath, dpi=110, facecolor='w')
    plt.close(fig)


def write_conditions(path, P, B, levels):
    # 이번 실험의 고정 조건 기록 (보고서에 그대로 옮길 수 있게)
    lines = [
        f'실험 일시: {datetime.now():%Y-%m-%d %H:%M}',
        '',
        '[네트워크]',
        f'  Grid {P.numPlanes} x {P.satsPerPlane}, 출발 ({P.srcSat[0]},{P.srcSat[1]}) -> 도착 ({P.dstSat[0]},{P.dstSat[1]}), Grid 끝 미연결',
        f'  링크 지연 상/하 {P.linkDelay[0]} step, 좌/우 {P.linkDelay[2]} step, 처리 지연 {P.processingDelay} step',
        f'  링크 용량 {P.linkCapacity} packets/step, 링크별 큐 {P.queueMax} packets',
        '',
        '[주 흐름 패킷]',
        f'  생성 {P.genRate} packets/s (일정 간격), 크기 {P.packetSize} Byte',
        f'  기한 {P.deadline} step (= ms), TTL {P.ttlInit}',
        f'  시뮬레이션 {P.simTime} step ({P.simTime * P.stepTime:.0f}초), 1 step = {P.stepTime * 1e3:.0f} ms',
        '',
        '[라우팅]',
        f'  B (Liu 단순화): k = {P.k}, X = {P.X}, Y = {P.Y}',
        f'  평가 ε = 0, 학습 데이터 수집 ε = {B.trainEpsilon}',
        '',
        '[배경 트래픽] (고정 경로: 목적지 쪽 좌/우 먼저, 기한 없음, 지표 계산에서 제외)',
        f'  흐름: ' + ', '.join(f'({a[0]},{a[1]})->({b[0]},{b[1]})' for a, b in B.flows),
        f'  ON/OFF 평균 {B.onMean} / {B.offMean} step (지수분포), TTL {B.ttl}',
        '  부하 단계 (ON일 때 흐름별 packets/step): ' + ', '.join(f'{B.levelNames[lv]} {B.levels[lv]}' for lv in levels),
        '',
        '[시드]',
        f'  평가용: {B.evalSeeds[:B.numSeeds]}',
        f'  학습용: {B.trainSeeds[:B.numSeeds]}',
        '  (시드 하나가 배경 ON/OFF 패턴과 ε 무작위 선택에 같이 쓰임)',
    ]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    B = config_bg()
    P = config_isl()
    levels = [lv for lv in B.levels if B.runLevels.get(lv)]
    jobs = []
    if B.runEval:
        jobs += [('eval', lv, s) for lv in levels for s in B.evalSeeds[:B.numSeeds]]
    if B.runTrain:
        jobs += [('train', lv, s) for lv in levels for s in B.trainSeeds[:B.numSeeds]]
    if not jobs:
        raise SystemExit('config_bg.py에서 runEval / runTrain과 runLevels를 하나 이상 켜 주세요.')

    print(f'부하 단계 {[B.levelNames[lv] for lv in levels]} x 시드 {B.numSeeds}개 '
          f'(평가 {B.runEval}, 학습 데이터 {B.runTrain}) = {len(jobs)}번 실행, 동시 {B.numWorkers}개')

    tic = time.time()
    rows = []
    with Pool(B.numWorkers) as pool:
        for k, row in enumerate(pool.imap_unordered(one_run, jobs), 1):
            rows.append(row)
            print(f'  [{k}/{len(jobs)}] {row["name"]} ({GROUP[row["mode"]]}): '
                  f'기한 내 도착률 {row["onTimeRate"] * 100:.1f}%  ({row["runTime_s"]:.0f}s)')
    order = {lv: i for i, lv in enumerate(levels)}
    rows.sort(key=lambda r: (r['mode'], order[r['level']], r['seed']))

    for mode in ['eval', 'train']:
        group = [r for r in rows if r['mode'] == mode]
        if not group:
            continue
        outDir = os.path.join(expDir, GROUP[mode])
        os.makedirs(outDir, exist_ok=True)
        write_csv(group, os.path.join(outDir, f'{mode}_runs.csv'))
        stats = stats_rows(group, levels)
        write_csv(stats, os.path.join(outDir, f'{mode}_stats.csv'))
        print(f'\n===== {"평가" if mode == "eval" else "학습 데이터"} 결과 (평균 ± 표준편차, 시드 {B.numSeeds}개) =====')
        for level in levels:
            line = [f'{s["name"]} {s["mean"]:.2f} ± {s["std"]:.2f}{s["unit"]}'
                    for s in stats if s['level'] == level and s['metric'] in ('onTimeRate', 'avgLatency_ms', 'maxConsecLoss')]
            print(f'  {B.levelNames[level]} ({B.levels[level]}): ' + ',  '.join(line))
        if mode == 'eval':
            plot_summary(group, levels, B, os.path.join(outDir, 'eval_summary.png'))
        write_conditions(os.path.join(outDir, 'conditions.txt'), P, B, levels)
        save_results(baseDir, outDir, summary_dir(P.routeName, GROUP[mode], levels))   # 요약 + 코드 복사
    print(f'\n총 {time.time() - tic:.0f}초')
