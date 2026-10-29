# 배경 트래픽 검증 스크립트
#   python check_bg.py save   : (엔진 코드를 고치기 전/고친 뒤 기준 시점에 한 번) 배경 없는 결과를 baseline_nobg.npz로 저장
#   python check_bg.py check  : 회귀 테스트(배경 끔) + 핫스팟 시나리오 보존 법칙/재현성/난이도 분포 점검
import sys

import numpy as np

from bg_traffic import describe_hotspots, link_load_report, sample_hotspots
from build_grid import build_grid
from config_isl import config_isl
from run_isl_sim import run_isl_sim

KEYS = ['genTime', 'endTime', 'hops', 'status', 'decisionLog', 'timeline']


def run(eps, bg, seed=None, simTime=30000):
    P = config_isl()
    P.simTime = simTime               # 빠른 확인용
    P.bgEnable = bg
    picked = rates = None
    if bg:
        picked, rates = sample_hotspots(P, build_grid(P), P.bgScenarioSeed if seed is None else seed)
    return P, run_isl_sim(P, int(P.genRate), eps, P.randomSeed, False), picked, rates


def conserved(R):
    b = R.bg
    return (b['generated'] - b['srcDrop']) == (b['delivered'] + b['overflow'] + b['ttlExpired'] + b['inFlight'])


def main_stats(R):
    st = R.status
    n = R.numPackets
    lat = (R.endTime - R.genTime)[(st == 1) | (st == 2)]
    return dict(n=n, onTime=np.mean(st == 1), overflow=np.sum(st == 4) / n,
                late=(np.sum(st == 2) + np.sum(st == 3)) / n, lat=lat.mean(), p99=np.percentile(lat, 99))


if len(sys.argv) < 2 or sys.argv[1] not in ('save', 'check'):
    sys.exit('사용법: python check_bg.py save | check')

if sys.argv[1] == 'save':
    out = {}
    for eps in (0, 0.1):
        P, R, _, _ = run(eps, False)
        for k in KEYS:
            out[f'{k}_{eps}'] = getattr(R, k)
    np.savez('baseline_nobg.npz', **out)
    print('baseline_nobg.npz 저장 완료 (배경 끈 기준 결과)')
else:
    base = np.load('baseline_nobg.npz')
    for eps in (0, 0.1):
        P, R, _, _ = run(eps, False)
        same = all(np.array_equal(base[f'{k}_{eps}'], getattr(R, k)) for k in KEYS)
        print(f'[1 회귀] eps={eps}, 배경 끔 -> 저장해 둔 결과와 동일: {same}')
    print('    (설정값 linkCapacity/queueMax/deadline 등을 바꿨다면 False가 정상: python check_bg.py save 로 기준을 다시 저장)')

    P, R, picked, rates = run(0, True)
    print(f'[2 시나리오 시드 {P.bgScenarioSeed}] 핫스팟 {len(picked)}개: {describe_hotspots(picked, rates, P)}')
    print('    혼잡 링크 (최대 > 링크 용량인 곳):')
    link_load_report(P, R.grid)
    b = R.bg
    left = b['generated'] - b['srcDrop']
    done = b['delivered'] + b['overflow'] + b['ttlExpired'] + b['inFlight']
    print(f'[3 보존 법칙] 생성-srcDrop={left}, 도착+오버플로+TTL+이동중={done} -> 일치: {left == done}')
    print(f'    배경 통계: {b}  (srcDrop은 0이어야 정상)')
    print(f'[4 링크 용량] 링크별 최대 평균 전송 {R.linkSent.max() / R.endStep:.2f} packets/step (용량 {P.linkCapacity} 이하여야 정상)')

    _, R2, _, _ = run(0, True)
    print(f'[5 재현성] 같은 시드로 두 번 실행 -> 결과 동일: {np.array_equal(R.status, R2.status) and np.array_equal(R.endTime, R2.endTime)}')

    print('[6 시나리오별 주 흐름 결과] (시드를 바꾸면 위치가 바뀌고 난이도도 달라져야 함, 20초 실행)')
    allOk = True
    for seed in (1, 2, 3, 4, 5):
        Ps, Rs, pk, rt = run(0, True, seed, simTime=20000)
        ok = conserved(Rs) and Rs.bg['srcDrop'] == 0
        allOk &= ok
        m = main_stats(Rs)
        print(f'    시드 {seed}: 기한 내 {m["onTime"]:.3f} 오버플로 {m["overflow"]:.3f} 기한 초과 {m["late"]:.3f} '
              f'평균 지연 {m["lat"]:.1f} P99 {m["p99"]:.0f} | 보존/srcDrop 정상: {ok} | {describe_hotspots(pk, rt, Ps)}')
    print(f'    모든 시드에서 보존 법칙 + srcDrop 0: {allOk}')
