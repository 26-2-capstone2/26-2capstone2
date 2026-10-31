# 실시간 실행기 - 웹 화면(3-1 시뮬레이터)에서 누른 대로 학습/평가를 돌리고, 상태를 화면으로 보냄
#
# 학습 순서는 rl/train_rl.py와 같음 (혼잡 단계를 돌아가며, 시드 1001부터, 에피소드 끝마다 기록)
# 시뮬레이터 안 상태는 P.stepHook(매 step 끝)으로 받고, 0.1초마다 한 번씩 화면에 보낼 묶음(snapshot)을 만듦
import queue
import threading
import time

import numpy as np

from routing.C_RL import STATE as C_STATE, set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim
from web.schema import build_config

LOSS = (2, 3, 4, 5)
SPEEDS = {'slow': 0.02, 'normal': 0.002, 'max': 0.0}   # step마다 쉬는 시간 (초). 최대는 계산 속도 그대로


class StopRun(Exception):
    pass


def loss_runs(status):
    # 생성 순서로 이어진 손실 구간 길이 (아직 안 끝난 패킷, 도착 패킷에서 끊음)
    runs, cur = [], 0
    for st in status:
        if st in LOSS:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


class LiveRunner:
    def __init__(self):
        self.lock = threading.Lock()
        self.subs = []                 # 화면 연결마다 queue 하나
        self.thread = None
        self.agent = None
        self.overrides = {}
        self.cmd = dict(paused=False, stop=False, steps=0, speed='normal')
        self.state = dict(status='idle', mode='train', level='rotate', episode=0, totalEpisodes=0)
        self.history = []              # 에피소드별 기록 (train_log.csv와 같은 열)
        self.events = []
        self.selected = None           # 3-2: Q값을 볼 위성 (p, s). None이면 출발 위성
        self.selRecent = []            # 선택한 위성의 최근 결정
        self.lastAct = {}              # 위성별 마지막으로 고른 방향 (정책 지도)

    # ---- 화면 연결 ----
    def subscribe(self):
        q = queue.Queue(maxsize=50)
        with self.lock:
            self.subs.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def broadcast(self, msg):
        with self.lock:
            for q in list(self.subs):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass   # 화면이 느리면 그 묶음은 건너뜀 (다음 묶음이 곧 옴)

    def info(self):
        return dict(state=self.state, history=self.history[-200:], events=self.events[-60:], speed=self.cmd['speed'],
                    start=getattr(self, 'lastStart', None))

    # ---- 조작 ----
    def control(self, action, opts):
        if action == 'start':
            if self.thread and self.thread.is_alive():
                self.cmd['paused'] = False
                return 'resumed'
            self.cmd.update(paused=False, stop=False, steps=0)
            self.overrides = opts.get('overrides', self.overrides)
            self.state.update(mode=opts.get('mode', 'train'), level=opts.get('level', 'rotate'))
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            return 'started'
        if action == 'pause':
            self.cmd['paused'] = True
            return 'paused'
        if action == 'step':          # 10 ms만 진행하고 멈춤
            if not (self.thread and self.thread.is_alive()):
                self.control('start', opts)
            self.cmd.update(paused=False, steps=10)
            return 'stepped'
        if action == 'stop':
            self.cmd['stop'] = True
            self.cmd['paused'] = False
            return 'stopping'
        if action == 'reset':         # 신경망을 처음 상태로 (멈춘 뒤에만)
            if self.thread and self.thread.is_alive():
                return 'busy'
            self.agent = None
            self.history, self.events = [], []
            self.state.update(status='idle', episode=0)
            self.broadcast(dict(type='reset'))
            return 'reset'
        if action == 'speed':
            self.cmd['speed'] = opts.get('speed', 'normal')
            return 'ok'
        if action == 'select':        # 3-2에서 볼 위성 바꾸기
            self.selected = (int(opts['p']), int(opts['s']))
            self.selRecent = []
            return 'ok'
        return 'unknown'

    # ---- 실행 ----
    def _run(self):
        self.state.update(status='loading', error=None)   # 처음 실행은 PyTorch를 불러오느라 몇 초 걸림
        self.broadcast(dict(type='state', state=self.state))
        from rl.rl_agent import DQNAgent      # PyTorch는 실행할 때만 필요
        from rl.rl_collector import Collector
        P, RL = build_config(self.overrides)
        P.routeName = 'C_RL'
        train = self.state['mode'] == 'train'
        if self.agent is None:
            self.agent = DQNAgent(RL)
        agent = self.agent
        collector = Collector(agent, P, RL, learn=True) if train else None
        set_agent(agent, RL, explore=train, collector=collector)
        levels = RL.trainLevels if self.state['level'] == 'rotate' else [self.state['level']]
        nEp = RL.trainEpisodes if train else P.numEpisodes
        startEp = len(self.history) if train else 0
        self.state.update(status='running', totalEpisodes=nEp)
        self.collector = collector
        if self.selected is None:
            self.selected = (int(P.srcSat[0]), int(P.srcSat[1]))
        import sim.run_isl_sim as SIM
        origRoute = SIM.ROUTES['C_RL']
        SIM.ROUTES['C_RL'] = self._wrap_route(origRoute, agent, train)   # 원래 C_RL은 그대로, 결정을 엿보기만 함
        try:
            for ep in range(startEp, nEp):
                level = levels[ep % len(levels)]
                seed = (RL.trainSeedStart + ep) if train else (P.randomSeed + ep)
                from config_isl import apply_bg_level
                apply_bg_level(P, level)
                G = build_grid(P)
                picked, rates = sample_hotspots(P, G, seed)
                self._begin_episode(P, G, ep, level, seed, picked, rates)
                if collector:
                    collector.reset_stats()
                P.stepHook = self._hook
                t0 = time.time()
                R = run_isl_sim(P, P.genRate, 0, seed, False)
                if collector:
                    collector.finish()
                self._end_episode(R, P, agent, collector, ep, level, seed, time.time() - t0)
        except StopRun:
            pass
        except Exception as e:     # 오류는 화면에 그대로 보여 줌 (나중에 들어온 화면도 state.error로 봄)
            self.state['error'] = f'{type(e).__name__}: {e}'
            self.broadcast(dict(type='error', message=self.state['error']))
        finally:
            SIM.ROUTES['C_RL'] = origRoute
            P.stepHook = None
            self.state['status'] = 'idle'
            self.broadcast(dict(type='state', state=self.state))

    def _wrap_route(self, route, agent, train):
        # C_RL을 그대로 부르고, 방금 결정(관측, 마스크, 행동)을 기록. 선택한 위성이면 Q값도 계산
        import torch

        def wrapped(p, s, queueLen, G, P, **kw):
            out = route(p, s, queueLen, G, P, **kw)
            obs, mask, action = C_STATE.last
            self.lastAct[(p, s)] = action + 1
            if (p, s) == self.selected:
                with torch.no_grad():
                    q = agent.q(torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)).squeeze(0).numpy()
                allowed = [d for d in range(4) if mask[d] > 0]
                best = max(allowed, key=lambda d: q[d])
                eps = agent.epsilon() if train else 0.0
                prob = [0.0] * 4
                for d in allowed:
                    prob[d] = eps / len(allowed) + (1 - eps if d == best else 0.0)
                # 방향별로 막힌 이유: 관측 12~15 링크 유무, 0~3 큐 ÷ 200
                why = []
                for d in range(4):
                    if obs[12 + d] == 0:
                        why.append('링크 없음')
                    elif mask[d] > 0:
                        why.append('가능')
                    elif obs[d] >= 1.0:
                        why.append('큐 꽉 참')
                    else:
                        why.append('기한 안에 못 감')
                dec = dict(t=int(kw.get('t', 0)), sat=[p, s], q=[round(float(q[d]), 3) if mask[d] > 0 else None for d in range(4)],
                           qRaw=[round(float(v), 3) for v in q], mask=[int(m) for m in mask], action=action, random=action != best,
                           best=best, eps=round(eps, 3), prob=[round(x, 3) for x in prob], why=why, obs=[round(float(v), 3) for v in obs],
                           remDeadline=int(kw.get('remDeadline') or 0), ttl=int(kw.get('ttl') or 0), hops=int(kw.get('hops') or 0))
                self.selRecent.append(dec)
                self.selRecent = self.selRecent[-30:]
            return out
        return wrapped

    def _begin_episode(self, P, G, ep, level, seed, picked, rates):
        self.P, self.G = P, G
        links = []
        for p in range(P.numPlanes):
            for s in range(P.satsPerPlane):
                for d in G.validDirs[p][s]:
                    links.append((int(G.linkId[p, s, d - 1]), p, s, d))
        self.linkIds = np.array([l[0] for l in links])
        self.linkFrom = {l[0]: (l[1], l[2]) for l in links}
        self.prevStatus = None
        self.lastSent = 0.0
        hot = [dict(p=int(c[0]), s=int(c[1]), dir=int(c[2]), load=round(float(r) / P.linkCapacity, 2)) for c, r in zip(picked, rates)]
        self.state.update(episode=ep + 1, levelNow=level, seed=seed, simTime=P.simTime)
        self.lastStart = dict(type='episode_start', state=self.state,
                              grid=dict(planes=P.numPlanes, sats=P.satsPerPlane, src=[int(x) for x in P.srcSat], dst=[int(x) for x in P.dstSat],
                                        queueMax=P.queueMax, burstMinLen=P.burstMinLen),
                              links=[dict(p=l[1], s=l[2], dir=l[3]) for l in links], hotspots=hot)
        self.broadcast(self.lastStart)   # 중간에 들어온 화면도 받을 수 있게 마지막 것을 남겨 둠 (info의 start)

    def _hook(self, t, queueLen, status, curP, curS, onLink, numPackets):
        c = self.cmd
        if c['stop']:
            raise StopRun()
        if c['steps'] > 0:
            c['steps'] -= 1
            if c['steps'] == 0:
                c['paused'] = True
                self._snapshot(t, queueLen, status, curP, curS, onLink, numPackets)
        while c['paused'] and not c['stop']:
            time.sleep(0.05)
        if c['stop']:
            raise StopRun()
        delay = SPEEDS.get(c['speed'], 0.0)
        if delay:
            time.sleep(delay)
        now = time.monotonic()
        if now - self.lastSent >= 0.1:
            self.lastSent = now
            self._snapshot(t, queueLen, status, curP, curS, onLink, numPackets)

    def _snapshot(self, t, queueLen, status, curP, curS, onLink, numPackets):
        P = self.P
        st = status[:numPackets]
        # 새로 끝난 손실 패킷 -> 이벤트
        if self.prevStatus is not None and len(self.prevStatus) <= numPackets:
            n0 = len(self.prevStatus)
            newly = np.flatnonzero((st[:n0] != self.prevStatus) & np.isin(st[:n0], LOSS))
            for i in newly[-8:]:
                kind = {2: '목적지에 늦게 도착', 3: '가는 중 기한 초과', 4: '큐 넘침', 5: 'TTL 만료'}[int(st[i])]
                self._event(t, '손실', f'패킷 #{int(i)}  위성 ({int(curP[i])}, {int(curS[i])})  {kind}', 'loss',
                            pos=[int(curP[i]), int(curS[i])])
        runs = loss_runs(st.tolist())
        bursts = [r for r in runs if r >= P.burstMinLen]
        prevB = self.state.get('burstCount', 0) if self.prevStatus is not None else 0
        if len(bursts) > prevB:
            self._event(t, '연속 손실', f'{bursts[-1]}개 연속, 벌점 -{self.collector.RL.consecPenalty if self.collector else 0}', 'burst')
        self.prevStatus = st.copy()
        inflight = np.flatnonzero(st == 0)[-400:]
        pk = []
        for i in inflight:
            l = int(onLink[i])
            if l >= 0:
                fp, fs = self.linkFrom.get(l, (int(curP[i]), int(curS[i])))
                pk.append([fp, fs, int(curP[i]), int(curS[i])])
            else:
                pk.append([int(curP[i]), int(curS[i]), int(curP[i]), int(curS[i])])
        onTime = int((st == 1).sum())
        lost = int(np.isin(st, LOSS).sum())
        ended = onTime + lost
        self.state.update(t=int(t), burstCount=len(bursts))
        a, col = C_STATE.agent, self.collector
        learn = dict(epsilon=round(a.epsilon(), 3) if self.state['mode'] == 'train' else 0.0, buffer=len(a.buffer),
                     bufferSize=a.buffer.size, updates=a.numUpdates,
                     loss=round(float(np.mean(col.losses[-50:])), 5) if col and col.losses else None,
                     rewardHop=round(col.rewardHopSum, 2) if col else 0, rewardOutcome=round(col.rewardOutcomeSum, 2) if col else 0,
                     rewardBurst=round(col.rewardBurstSum, 2) if col else 0)
        self.broadcast(dict(type='snap', t=int(t), simTime=P.simTime, episode=self.state['episode'],
                            queues=queueLen[self.linkIds].astype(int).tolist(), packets=pk,
                            stats=dict(generated=int(numPackets), onTime=onTime, lost=lost, inflight=int(len(np.flatnonzero(st == 0))),
                                       onTimeRate=round(onTime / ended * 100, 2) if ended else 0.0,
                                       lossRate=round(lost / ended * 100, 2) if ended else 0.0,
                                       maxConsecLoss=max(runs) if runs else 0, burstCount=len(bursts)),
                            timeline=st[-120:].tolist(), learn=learn, paused=self.cmd['paused'],
                            selected=dict(sat=list(self.selected) if self.selected else None, recent=self.selRecent[-12:]),
                            policy=[[p, s, d] for (p, s), d in self.lastAct.items()]))

    def _event(self, t, kind, text, cls, pos=None):
        e = dict(t=int(t), episode=self.state['episode'], kind=kind, text=text, cls=cls, pos=pos)
        self.events.append(e)
        self.events = self.events[-200:]
        self.broadcast(dict(type='event', event=e))

    def _end_episode(self, R, P, agent, collector, ep, level, seed, secs):
        st = R.status
        runs = loss_runs(st.tolist())
        row = dict(episode=ep + 1, level=level, seed=seed,
                   onTimeRate=round(float((st == 1).mean()) * 100, 2), lossRate=round(float(np.isin(st, LOSS).mean()) * 100, 2),
                   maxConsecLoss=max(runs) if runs else 0, burstCount=sum(1 for r in runs if r >= P.burstMinLen),
                   epsilon=round(agent.epsilon(), 3) if collector else 0.0,
                   rewardHopSum=round(collector.rewardHopSum, 2) if collector else 0, rewardOutcomeSum=round(collector.rewardOutcomeSum, 2) if collector else 0,
                   rewardBurstSum=round(collector.rewardBurstSum, 2) if collector else 0, seconds=round(secs, 1))
        self.history.append(row)
        self.broadcast(dict(type='episode_end', row=row, state=self.state))
