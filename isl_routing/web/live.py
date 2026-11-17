# 실시간 실행기 - 웹 화면(3-1 시뮬레이터)에서 누른 대로 학습/평가를 돌리고, 상태를 화면으로 보냄
#
# 학습 순서는 rl/train_rl.py와 같음
#   혼잡 단계: 비율(trainLevelWeights)대로 무작위 (trainSeedStart로 순서 고정), 시드 1001부터
#   주 흐름: numFlows개. 학습 때는 흐름 0도 무작위 (flowZeroRandomTrain), 평가와 검증은 흐름 0 = (0,0) -> (5,5) 고정
#   배경 트래픽: 지역 핫스팟 방식 (bgMode = 'event')
#   검증: evalEvery 에피소드마다 학습을 멈추고 검증 시드(501~503)로 ε 0 평가
# 화면의 결과 숫자는 흐름 0 기준 (흐름 4개 전체 도착률은 옆에 작게)
# 시뮬레이터 안 상태는 P.stepHook(매 step 끝)으로 받고, 0.1초마다 한 번씩 화면에 보낼 묶음(snapshot)을 만듦
import queue
import threading
import time

import numpy as np

from config_isl import apply_bg_level
from routing.route_C import STATE as C_STATE, set_agent
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim
from web.schema import build_config

LOSS = (2, 3, 4, 5)
LOSS_NAME = {2: '목적지에 늦게 도착', 3: '가는 중 기한 초과', 4: '큐 넘침', 5: 'TTL 만료'}
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


def level_sequence(RL, n, seedStart):
    # 에피소드별 혼잡 단계 (train_rl.train_level_sequence와 같음)
    if getattr(RL, 'trainLevelMode', 'cycle') != 'weighted':
        return [RL.trainLevels[ep % len(RL.trainLevels)] for ep in range(n)]
    w = np.array([RL.trainLevelWeights[lv] for lv in RL.trainLevels], dtype=float)
    rng = np.random.RandomState(seedStart)
    return [str(lv) for lv in rng.choice(RL.trainLevels, size=n, p=w / w.sum())]


class LiveRunner:
    def __init__(self):
        self.lock = threading.Lock()
        self.subs = []                 # 화면 연결마다 queue 하나
        self.thread = None
        self.agent = None
        self.overrides = {}
        self.cmd = dict(paused=False, stop=False, steps=0, speed='normal')
        self.state = dict(status='idle', mode='train', level='ratio', episode=0, totalEpisodes=0)
        self.history = []              # 에피소드별 기록 (흐름 0 기준)
        self.valHistory = []           # 검증 평가 기록 (흐름 0, 단계별)
        self.events = []
        self.selected = None           # 3-2: Q값을 볼 위성 (p, s). None이면 흐름 0 출발 위성
        self.selRecent = []            # 선택한 위성의 최근 결정
        self.lastAct = {}              # 위성별 마지막으로 고른 방향 (정책 지도)
        self.validating = False

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
        return dict(state=self.state, history=self.history[-200:], val=self.valHistory[-200:], events=self.events[-60:],
                    speed=self.cmd['speed'], start=getattr(self, 'lastStart', None))

    # ---- 조작 ----
    def control(self, action, opts):
        if action == 'start':
            if self.thread and self.thread.is_alive():
                self.cmd['paused'] = False
                return 'resumed'
            self.cmd.update(paused=False, stop=False, steps=0)
            self.overrides = opts.get('overrides', self.overrides)
            self.state.update(mode=opts.get('mode', 'train'), level=opts.get('level', 'ratio'))
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
            self.history, self.valHistory, self.events = [], [], []
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
        P.routeName = 'routeC'
        train = self.state['mode'] == 'train'
        if self.agent is None:
            self.agent = DQNAgent(RL)
        agent = self.agent
        collector = Collector(agent, P, RL, learn=True) if train else None
        set_agent(agent, RL, explore=train, collector=collector)
        nEp = RL.trainEpisodes if train else P.numEpisodes
        seedStart = RL.trainSeedStart if train else P.randomSeed
        if self.state['level'] == 'ratio':
            levels = level_sequence(RL, nEp, seedStart)
        else:
            levels = [self.state['level']] * nEp
        startEp = len(self.history) if train else 0
        self.state.update(status='running', totalEpisodes=nEp)
        self.collector = collector
        if self.selected is None:
            self.selected = (int(P.srcSat[0]), int(P.srcSat[1]))
        import sim.run_isl_sim as SIM
        origRoute = SIM.ROUTE_FUNCS['routeC']
        SIM.ROUTE_FUNCS['routeC'] = self._wrap_route(origRoute, agent, train)   # 원래 route_C는 그대로, 결정을 엿보기만 함
        try:
            for ep in range(startEp, nEp):
                level = levels[ep]
                seed = seedStart + ep
                apply_bg_level(P, level)
                G = build_grid(P)
                P.flowZeroRandom = bool(train and RL.flowZeroRandomTrain)
                sample_hotspots(P, G, seed)          # 주 흐름(P.mainFlows)과 지역 핫스팟(P.bgEvents)도 여기서 정함
                self._begin_episode(P, G, ep, level, seed)
                if collector:
                    collector.reset_stats()
                P.stepHook = self._hook
                t0 = time.time()
                R = run_isl_sim(P, P.genRate, 0, seed, False)
                if collector:
                    collector.finish()
                self._end_episode(R, P, agent, collector, ep, level, seed, time.time() - t0)
                if train and RL.evalEvery > 0 and ((ep + 1) % RL.evalEvery == 0 or ep + 1 == nEp):
                    self._validate(P, RL, agent, collector, ep + 1)
        except StopRun:
            pass
        except Exception as e:     # 오류는 화면에 그대로 보여 줌 (나중에 들어온 화면도 state.error로 봄)
            self.state['error'] = f'{type(e).__name__}: {e}'
            self.broadcast(dict(type='error', message=self.state['error']))
        finally:
            SIM.ROUTE_FUNCS['routeC'] = origRoute
            P.stepHook = None
            self.validating = False
            set_agent(agent, RL, explore=False, collector=None)
            self.state['status'] = 'idle'
            self.broadcast(dict(type='state', state=self.state))

    def _validate(self, P, RL, agent, collector, episode):
        # 검증 평가: train_rl.validate와 같은 조건 (ε 0, 학습 없음, 흐름 0 고정). 화면 숫자는 흐름 0 기준
        self.validating = True
        self.state['status'] = 'validating'
        self.broadcast(dict(type='state', state=self.state))
        set_agent(agent, RL, explore=False, collector=None)
        P.stepHook = self._stop_only
        t0 = time.time()
        for level in RL.valLevels:
            apply_bg_level(P, level)
            G = build_grid(P)
            st0, stAll, runs = [], [], []
            for seed in RL.valSeeds:
                P.flowZeroRandom = False
                sample_hotspots(P, G, seed)
                R = run_isl_sim(P, P.genRate, 0, seed, False)
                s0 = R.status[R.packetFlow == 0]
                st0.append(s0)
                stAll.append(R.status)
                runs += loss_runs(s0.tolist())
            st0, stAll = np.concatenate(st0), np.concatenate(stAll)
            minutes = len(RL.valSeeds) * P.simTime * P.stepTime / 60
            bursts = [r for r in runs if r >= P.burstMinLen]
            row = dict(episode=episode, level=level, onTimeRate=round(float((st0 == 1).mean()) * 100, 2),
                       allOnTimeRate=round(float((stAll == 1).mean()) * 100, 2),
                       burstPerMin=round(len(bursts) / minutes, 2) if minutes else 0.0,
                       maxConsecLoss=max(runs) if runs else 0)
            self.valHistory.append(row)
            self.broadcast(dict(type='val', row=row))
        set_agent(agent, RL, explore=True, collector=collector)
        self.validating = False
        self.state['status'] = 'running'
        self._event(0, '검증', f'에피소드 {episode} 뒤 검증 끝 ({time.time() - t0:.0f}초)', 'val')
        self.broadcast(dict(type='state', state=self.state))

    def _stop_only(self, *args):
        # 검증 중에는 화면을 그리지 않고 멈춤 버튼만 확인
        c = self.cmd
        while c['paused'] and not c['stop']:
            time.sleep(0.05)
        if c['stop']:
            raise StopRun()

    def _wrap_route(self, route, agent, train):
        # route_C를 그대로 부르고, 방금 결정(관측, 마스크, 행동)을 기록. 선택한 위성이면 Q값도 계산
        import torch

        def wrapped(p, s, queueLen, G, P, **kw):
            out = route(p, s, queueLen, G, P, **kw)
            if self.validating:
                return out
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
                why = ['가능' if mask[d] > 0 else '링크 없음' for d in range(4)]   # 마스크는 링크 없는 방향만 막음
                dec = dict(t=int(kw.get('t', 0)), sat=[p, s], dst=[int(G.dstSat[0]), int(G.dstSat[1])],
                           q=[round(float(q[d]), 3) if mask[d] > 0 else None for d in range(4)],
                           qRaw=[round(float(v), 3) for v in q], mask=[int(m) for m in mask], action=action, random=action != best,
                           best=best, eps=round(eps, 3), prob=[round(x, 3) for x in prob], why=why, obs=[round(float(v), 3) for v in obs],
                           remDeadline=int(kw.get('remDeadline') or 0), ttl=int(kw.get('ttl') or 0), hops=int(kw.get('hops') or 0))
                self.selRecent.append(dec)
                self.selRecent = self.selRecent[-30:]
            return out
        return wrapped

    def _begin_episode(self, P, G, ep, level, seed):
        self.P, self.G = P, G
        links = []
        for p in range(P.numPlanes):
            for s in range(P.satsPerPlane):
                for d in G.validDirs[p][s]:
                    links.append((int(G.linkId[p, s, d - 1]), p, s, d))
        self.linkIds = np.array([l[0] for l in links])
        self.linkFrom = {l[0]: (l[1], l[2]) for l in links}
        self.flows = [[list(a), list(b)] for a, b in P.mainFlows]
        self.prevStatus = {}
        self.prevBurst = 0
        self.lastSent = 0.0
        # 지역 핫스팟 링크 (기본 부하는 모든 링크라 그리지 않음): [p, s, 방향, 시작 ms, 끝 ms]
        hot = []
        for ((sp, ss), (np_, ns_)), (a, b) in zip(P.bgFlows, P.bgEvents):
            if (a, b) == (1, P.simTime):
                continue
            d = next(d for d in G.validDirs[sp][ss] if (int(G.nbrP[sp, ss, d - 1]), int(G.nbrS[sp, ss, d - 1])) == (np_, ns_))
            hot.append([int(sp), int(ss), int(d), int(a), int(b)])
        self.state.update(episode=ep + 1, levelNow=level, seed=seed, simTime=P.simTime)
        self.lastStart = dict(type='episode_start', state=self.state,
                              grid=dict(planes=P.numPlanes, sats=P.satsPerPlane, src=self.flows[0][0], dst=self.flows[0][1],
                                        queueMax=P.queueMax, burstMinLen=P.burstMinLen, deadline=P.deadline, topology=P.topology),
                              flows=self.flows, links=[dict(p=l[1], s=l[2], dir=l[3]) for l in links], hotspots=hot)
        self._event(0, '핫스팟', f'에피소드 {ep + 1} ({level}): 지역 핫스팟 링크 {len(hot)}개 예정', 'hot')
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
        # 패킷 id는 흐름별 묶음 (흐름 f = f x perFlow부터, 지금까지 흐름마다 seq개 생성)
        P = self.P
        nF = len(self.flows)
        perFlow, seq = P.flowBlock, numPackets // nF
        ids = [f * perFlow + np.arange(seq) for f in range(nF)]
        sts = [status[i] for i in ids]
        # 새로 끝난 손실 패킷 -> 이벤트 (모든 흐름, 흐름 번호 표시)
        for f in range(nF):
            prev = self.prevStatus.get(f)
            if prev is not None:
                n0 = len(prev)
                newly = np.flatnonzero((sts[f][:n0] != prev) & np.isin(sts[f][:n0], LOSS))
                for i in newly[-6:]:
                    pid = int(ids[f][i])
                    self._event(t, '손실', f'흐름 {f}  패킷 #{int(i)}  위성 ({int(curP[pid])}, {int(curS[pid])})  {LOSS_NAME[int(sts[f][i])]}',
                                'loss', pos=[int(curP[pid]), int(curS[pid])], flow=f)
            self.prevStatus[f] = sts[f].copy()
        st0 = sts[0]
        runs = loss_runs(st0.tolist())
        bursts = [r for r in runs if r >= P.burstMinLen]
        if len(bursts) > self.prevBurst:
            self._event(t, '연속 손실', f'흐름 0  {bursts[-1]}개 연속', 'burst', flow=0)
        self.prevBurst = len(bursts)
        # 이동 중인 패킷 [출발 p, s, 지금 p, s, 흐름]
        pk = []
        for f in range(nF):
            for i in ids[f][sts[f] == 0][-150:]:
                l = int(onLink[i])
                fp, fs = self.linkFrom.get(l, (int(curP[i]), int(curS[i]))) if l >= 0 else (int(curP[i]), int(curS[i]))
                pk.append([fp, fs, int(curP[i]), int(curS[i]), f])
        allSt = np.concatenate(sts)
        onTime, lost = int((st0 == 1).sum()), int(np.isin(st0, LOSS).sum())
        ended = onTime + lost
        aOn, aEnd = int((allSt == 1).sum()), int((allSt != 0).sum())
        self.state.update(t=int(t), burstCount=len(bursts))
        a, col = C_STATE.agent, self.collector
        learn = dict(epsilon=round(a.epsilon(), 3) if self.state['mode'] == 'train' else 0.0, buffer=len(a.buffer),
                     bufferSize=a.buffer.size, updates=a.numUpdates,
                     loss=round(float(np.mean(col.losses[-50:])), 5) if col and col.losses else None,
                     rewardHop=round(col.rewardHopSum, 2) if col else 0, rewardOutcome=round(col.rewardOutcomeSum, 2) if col else 0,
                     rewardBurst=round(col.rewardBurstSum, 2) if col else 0)
        self.broadcast(dict(type='snap', t=int(t), simTime=P.simTime, episode=self.state['episode'],
                            queues=queueLen[self.linkIds].astype(int).tolist(), packets=pk,
                            stats=dict(generated=int(seq), onTime=onTime, lost=lost, inflight=int((st0 == 0).sum()),
                                       onTimeRate=round(onTime / ended * 100, 2) if ended else 0.0,
                                       lossRate=round(lost / ended * 100, 2) if ended else 0.0,
                                       maxConsecLoss=max(runs) if runs else 0, burstCount=len(bursts),
                                       allOnTimeRate=round(aOn / aEnd * 100, 2) if aEnd else 0.0),
                            timeline=st0[-120:].tolist(), learn=learn, paused=self.cmd['paused'],
                            selected=dict(sat=list(self.selected) if self.selected else None, recent=self.selRecent[-12:]),
                            policy=[[p, s, d] for (p, s), d in self.lastAct.items()]))

    def _event(self, t, kind, text, cls, pos=None, flow=None):
        e = dict(t=int(t), episode=self.state['episode'], kind=kind, text=text, cls=cls, pos=pos, flow=flow)
        self.events.append(e)
        self.events = self.events[-200:]
        self.broadcast(dict(type='event', event=e))

    def _end_episode(self, R, P, agent, collector, ep, level, seed, secs):
        st = R.status[R.packetFlow == 0]          # 흐름 0 기준
        runs = loss_runs(st.tolist())
        row = dict(episode=ep + 1, level=level, seed=seed,
                   onTimeRate=round(float((st == 1).mean()) * 100, 2), lossRate=round(float(np.isin(st, LOSS).mean()) * 100, 2),
                   allOnTimeRate=round(float((R.status == 1).mean()) * 100, 2),
                   maxConsecLoss=max(runs) if runs else 0, burstCount=sum(1 for r in runs if r >= P.burstMinLen),
                   epsilon=round(agent.epsilon(), 3) if collector else 0.0,
                   rewardHopSum=round(collector.rewardHopSum, 2) if collector else 0, rewardOutcomeSum=round(collector.rewardOutcomeSum, 2) if collector else 0,
                   rewardBurstSum=round(collector.rewardBurstSum, 2) if collector else 0, seconds=round(secs, 1))
        self.history.append(row)
        self.broadcast(dict(type='episode_end', row=row, state=self.state))
