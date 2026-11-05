# 학습 곡선 목표 판정 - 학습 안정화 계획 5~8번 (학습 속도, 학습 곡선, 수렴, 안정성)
#
# 실행 (isl_routing 폴더에서):
#   python analysis/learning_targets.py 학습폴더                    -> 학습 1회 판정
#   python analysis/learning_targets.py 학습폴더1 학습폴더2 학습폴더3   -> 학습 시드 여러 개 (시드 간 차이까지 판정)
#
# 입력: train_rl.py가 만든 eval_log.csv (검증 평가, ε 0)와 train_log.csv (학습 손실)
# 기준 곡선: 검증 단계(base, high, severe)의 기한 내 도착률 평균, 가로축은 누적 결정 수
# 저장: 첫 학습폴더에 learning_targets.md (판정표), learning_curve_eval.png (단계별 검증 곡선)
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # isl_routing를 import 경로에 추가

import numpy as np

# 목표치 (학습 안정화 계획)
TARGETS = dict(
    t50Min=0.20,          # T50: 전체 학습의 20% 이후
    t90Min=0.40,          # T90: 전체 학습의 40~70%
    t90Max=0.70,
    minPoints=25,         # 평가 점 25개 이상
    maxJump=15.0,         # 연속한 두 평가 점 사이 도착률 변화 15%p 이하
    convOnTime=2.0,       # 수렴: 최근 평가 3번 도착률 차이 2%p 이내
    convBurst=0.20,       #       최근 평가 3번 연속 손실(1분당)이 평균에서 ±20% 이내
    convLossEp=30,        #       최근 30 에피소드 동안 학습 손실이 계속 커지지 않음
    convMax=0.75,         #       수렴 시점이 전체 학습의 75% 이전
    dropMax=5.0,          # 안정성: 수렴 뒤 연속한 두 평가 사이 도착률 하락 5%p 이하
    seedStd=3.0,          #         학습 시드 간 최종 도착률 표준편차 3%p 이하
    minGain=5.0,          # 학습 진행: 최종 도착률이 시작보다 5%p 이상 올라야 T50, T90, 수렴을 판정 (평평한 곡선을 수렴으로 보지 않음)
    divergeRatio=10.0,    #         학습 손실이 직전 20 에피소드 중앙값의 10배 이상이면 발산
)


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def load_run(trainDir):
    # 검증 기록 -> 평가 점별 (누적 결정 수, 단계별 도착률, 단계별 1분당 연속 손실), 학습 기록 -> 에피소드별 학습 손실
    ev = read_csv(os.path.join(trainDir, 'eval_log.csv'))
    levels = sorted({r['level'] for r in ev}, key=['base', 'high', 'severe'].index)
    idx = sorted({int(r['evalIndex']) for r in ev})
    get = {(int(r['evalIndex']), r['level']): r for r in ev}
    dec = np.array([int(get[(i, levels[0])]['decisions']) for i in idx])
    ep = np.array([int(get[(i, levels[0])]['episode']) for i in idx])
    onTime = np.array([[float(get[(i, lv)]['onTimeRate']) for lv in levels] for i in idx])
    burst = np.array([[float(get[(i, lv)]['burstPerMin']) for lv in levels] for i in idx])
    tr = read_csv(os.path.join(trainDir, 'train_log.csv'))
    loss = np.array([float(r['meanLoss']) if r['meanLoss'] != '' else np.nan for r in tr])
    return dict(dir=trainDir, levels=levels, decisions=dec, episode=ep, onTime=onTime, burst=burst, loss=loss)


def crossing(dec, curve, start, final, frac):
    # 오른 폭의 frac에 처음 도달한 누적 결정 수 (없으면 None)
    goal = start + frac * (final - start)
    hit = np.flatnonzero(curve >= goal)
    return int(dec[hit[0]]) if len(hit) else None


def loss_not_increasing(loss, upToEpisode, window):
    # 최근 window 에피소드 학습 손실의 기울기가 0 이하인지 (손실이 아직 없으면 판정 불가로 통과)
    seg = loss[max(0, upToEpisode - window):upToEpisode]
    seg = seg[~np.isnan(seg)]
    if len(seg) < 3:
        return True
    return np.polyfit(np.arange(len(seg)), seg, 1)[0] <= 0


def judge(run):
    T = TARGETS
    dec, onTime, burst = run['decisions'], run['onTime'], run['burst']
    total = dec[-1] if dec[-1] > 0 else 1
    avg = onTime.mean(axis=1)                              # 단계 평균 도착률
    start, final = avg[0], avg[-3:].mean()
    res = dict(points=len(dec), total=int(dec[-1]), start=round(start, 2), final=round(final, 2))

    learned = final - start >= T['minGain']
    if learned:
        t50, t90 = crossing(dec, avg, start, final, 0.5), crossing(dec, avg, start, final, 0.9)
    else:
        t50 = t90 = None
    res['t50'] = None if t50 is None else round(t50 / total, 3)
    res['t90'] = None if t90 is None else round(t90 / total, 3)
    res['maxJump'] = round(float(np.abs(np.diff(onTime, axis=0)).max()), 2) if len(dec) > 1 else 0.0

    conv = None                                            # 수렴: 모든 단계가 조건 만족한 첫 평가 점
    for i in range(2, len(dec) if learned else 0):
        w = slice(i - 2, i + 1)
        okOn = (onTime[w].max(axis=0) - onTime[w].min(axis=0) <= T['convOnTime']).all()
        mean = burst[w].mean(axis=0)
        okBurst = np.all((np.abs(burst[w] - mean) <= T['convBurst'] * mean) | (mean < 0.05))
        if okOn and okBurst and loss_not_increasing(run['loss'], int(run['episode'][i]), T['convLossEp']):
            conv = i
            break
    res['conv'] = None if conv is None else round(dec[conv] / total, 3)
    res['dropAfterConv'] = (round(float(max(0.0, -np.diff(onTime[conv:], axis=0).min())), 2)
                            if conv is not None and conv < len(dec) - 1 else None)

    loss = run['loss']
    diverge = False
    for k in range(20, len(loss)):
        prev = loss[k - 20:k]
        prev = prev[~np.isnan(prev)]
        if len(prev) and not np.isnan(loss[k]) and loss[k] >= T['divergeRatio'] * np.median(prev):
            diverge = True
            break
    res['diverge'] = diverge

    ok = lambda c: '만족' if c else '미달'
    res['checks'] = [
        ('학습 진행 (시작보다 5%p 이상 상승)', round(final - start, 2), ok(learned)),
        ('T50 (전체의 20% 이후)', res['t50'], ok(res['t50'] is not None and res['t50'] >= T['t50Min'])),
        ('T90 (전체의 40~70%)', res['t90'], ok(res['t90'] is not None and T['t90Min'] <= res['t90'] <= T['t90Max'])),
        ('평가 점 25개 이상', res['points'], ok(res['points'] >= T['minPoints'])),
        ('급상승 15%p 이하', res['maxJump'], ok(res['maxJump'] <= T['maxJump'])),
        ('수렴 (전체의 75% 이전)', res['conv'], ok(res['conv'] is not None and res['conv'] <= T['convMax'])),
        ('수렴 뒤 하락 5%p 이하', res['dropAfterConv'], ok(res['dropAfterConv'] is not None and res['dropAfterConv'] <= T['dropMax'])),
        ('학습 손실 발산 없음', '발산' if diverge else '없음', ok(not diverge)),
    ]
    return res


def plot(runs, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from viz.viz_colors import use_korean_font, viz_colors
    C = viz_colors()
    use_korean_font(C)
    levels = runs[0]['levels']
    fig, axes = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
    fig.patch.set_facecolor('white')
    for j, lv in enumerate(levels):
        for k, run in enumerate(runs):
            kw = dict(color=C.series[j], lw=2 if k == 0 else 1, alpha=1 if k == 0 else 0.5,
                      marker='o', ms=3, label=lv if k == 0 else None)
            axes[0].plot(run['decisions'] / 1e6, run['onTime'][:, j], **kw)
            axes[1].plot(run['decisions'] / 1e6, run['burst'][:, j], **kw)
    res = judge(runs[0])
    total = runs[0]['decisions'][-1] / 1e6
    for name, frac, style in (('T50', res['t50'], ':'), ('T90', res['t90'], '--'), ('수렴', res['conv'], '-')):
        if frac is not None:
            for ax in axes:
                ax.axvline(frac * total, color=C.muted, ls=style, lw=1)
            axes[0].text(frac * total, 101, name, ha='center', fontsize=8, color=C.muted)
    axes[0].set_ylabel('기한 내 도착률 (%, 검증 ε 0)')
    axes[0].set_ylim(0, 105)
    axes[0].legend(frameon=False, loc='lower right')
    axes[1].set_ylabel('연속 손실 (1분당)')
    axes[1].set_xlabel('누적 결정 수 (백만)')
    for ax in axes:
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        ax.grid(axis='y', color=C.grid, lw=0.8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    dirs = sys.argv[1:]
    if not dirs:
        print('사용법: python analysis/learning_targets.py 학습폴더 [학습폴더 ...]')
        return
    runs = [load_run(d) for d in dirs]
    lines = ['# 학습 곡선 목표 판정', '', f'학습 폴더: {", ".join(dirs)}', '',
             'T50, T90, 수렴은 전체 누적 결정 수 대비 비율. 기준 곡선은 검증 단계 평균 기한 내 도착률 (ε 0)', '']
    finals = []
    for run in runs:
        res = judge(run)
        finals.append(res['final'])
        lines += [f'## {os.path.basename(os.path.normpath(run["dir"]))}', '',
                  f'- 평가 점 {res["points"]}개, 총 결정 {res["total"]:,}번, 시작 도착률 {res["start"]}%, '
                  f'최종 도착률(마지막 3점 평균) {res["final"]}%', '',
                  '| 목표 | 값 | 판정 |', '|---|---|---|']
        lines += [f'| {name} | {"-" if v is None else v} | {verdict} |' for name, v, verdict in res['checks']]
        lines.append('')
    if len(runs) > 1:
        std = float(np.std(finals, ddof=1))
        lines += ['## 학습 시드 간 차이', '',
                  f'- 최종 도착률: {", ".join(f"{x}%" for x in finals)}, 표준편차 {std:.2f}%p '
                  f'(목표 {TARGETS["seedStd"]}%p 이하: {"만족" if std <= TARGETS["seedStd"] else "미달"})', '']
    text = '\n'.join(lines)
    print(text)
    with open(os.path.join(dirs[0], 'learning_targets.md'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    plot(runs, os.path.join(dirs[0], 'learning_curve_eval.png'))
    print(f'저장: {os.path.join(dirs[0], "learning_targets.md")}, learning_curve_eval.png')


if __name__ == '__main__':
    main()
