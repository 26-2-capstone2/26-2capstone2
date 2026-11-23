"""연속 손실 정의, 종료 순서, 연속 손실 보상, 관측 24개, 기한 행동 마스크의 회귀 테스트."""

import unittest
import numpy as np

from analysis.burst_summary import burst_summary
from config_isl import config_isl
from rl.config_rl import config_rl
from rl.rl_agent import DQNAgent
from rl.rl_collector import Collector
from rl.rl_reward import burst_reward
from rl.rl_state import action_mask, obs_from_sim
from sim.link_history import LinkHistory
from sim.build_grid import build_grid
from sim.run_isl_sim import run_isl_sim


class FakeAgent:
    def __init__(self):
        self.transitions = []

    def remember(self, *transition):
        self.transitions.append(transition)

    def ready(self):
        return False


class ObjectiveTests(unittest.TestCase):
    def test_three_or_more_losses_are_one_burst(self):
        status = np.array([1, 1, 2, 3, 4, 1, 5, 1, 2, 3, 4, 4, 1])
        result = burst_summary(status, 3)
        self.assertEqual(result.lossRuns.tolist(), [3, 1, 4])
        self.assertEqual((result.burstCount, result.burstPackets, result.maxConsecLoss), (2, 7, 4))
        self.assertAlmostEqual(result.burstPacketRate, 7 / len(status))

    def test_episode_boundary_breaks_run_and_unfinished_is_rejected(self):
        status = np.array([2, 2, 2, 2])
        result = burst_summary(status, 3, np.array([0, 0, 1, 1]))
        self.assertEqual(result.lossRuns.tolist(), [2, 2])
        self.assertEqual(result.burstCount, 0)
        with self.assertRaisesRegex(ValueError, '종료되지 않은'):
            burst_summary(np.array([1, 0, 2]), 3)

    def _run_collector(self, results, order=None):
        # results: 패킷 번호 순서의 결과, order: 끝나는 순서 (없으면 번호 순)
        P = config_isl()
        RL = config_rl(P)
        agent = FakeAgent()
        collector = Collector(agent, P, RL)
        mask = np.ones(4, dtype=np.float32)
        status = np.zeros(len(results), dtype=int)
        for packet_id in range(len(results)):
            obs = np.full(RL.obsDim, packet_id, dtype=np.float32)
            collector.on_decision(packet_id, (obs, mask, 0), 0, True, int(P.linkDelay[0]))
        for packet_id in (order or range(len(results))):
            status[packet_id] = results[packet_id]
            collector.on_end([packet_id], status)
        self.assertEqual(collector.finish(), 0)
        hop = -P.linkDelay[0] / P.deadline
        rewards = {int(t[0][0]): t[2] - hop for t in agent.transitions}
        return P, RL, collector, rewards

    def test_burst_reward_covers_whole_run_and_counts_bursts(self):
        P = config_isl()
        RL = config_rl(P)
        self.assertEqual([round(burst_reward(k, P, RL), 2) for k in (1, 3, 4, 5, 10, 13, 20)],
                         [-0.3, -2.3, -0.3, -0.3, -0.3, -0.3, -0.3])   # 5차: 패킷당 -0.3, k = 3에 시작 벌점 -2.0
        total = lambda n: sum(burst_reward(k, P, RL) for k in range(1, n + 1))
        self.assertLess(2 * total(10), total(20))                      # 같은 20개 손실이면 둘로 쪼갠 쪽이 더 나쁨
        results = [1, 4, 4, 1] + [4] * 5 + [1]           # 단발 2개, 연속 5개
        _, RL, collector, rewards = self._run_collector(results, order=list(range(len(results)))[::-1])
        self.assertEqual(collector.numBurstPenalties, 5)
        for packet_id, expected in [(0, 0.5), (1, -0.1), (2, -0.1), (3, 0.5), (4, -0.3), (5, -0.3), (6, -2.3),
                                    (7, -0.3), (8, -0.3), (9, 0.5)]:
            self.assertAlmostEqual(rewards[packet_id], expected, msg=f'패킷 {packet_id}')

    def test_burst_at_episode_end_is_judged_at_finish(self):
        _, _, collector, rewards = self._run_collector([1, 4, 4])
        self.assertEqual(collector.numBurstPenalties, 0)
        self.assertAlmostEqual(rewards[1], -0.1)
        self.assertAlmostEqual(rewards[2], -0.1)

    def test_success_breaks_burst_even_if_packets_finish_out_of_order(self):
        _, _, collector, _ = self._run_collector([1, 4, 4, 1, 4], order=[2, 1, 4, 3, 0])
        self.assertEqual(collector.numBurstPenalties, 0)

    def test_deadline_mask_and_24_observations(self):
        P = config_isl()
        RL = config_rl(P)
        RL.stateMode, RL.obsDim = 'full', 24   # 이전 State 24개 계산 확인 (기본은 coarse 15개)
        G = build_grid(P)
        queue = np.zeros(G.numLinks, dtype=int)
        observed = obs_from_sim(1, 0, queue, G, P, RL, 43, 20)
        self.assertEqual(observed.values.shape, (24,))
        np.testing.assert_array_equal(observed.mask, [0, 1, 1, 1])   # 들어온 링크 없음: 없는 방향(상)만 막음
        RL.maskMode = 'noBack'
        observed = obs_from_sim(1, 0, queue, G, P, RL, 43, 20, backDir=3)
        np.testing.assert_array_equal(observed.mask, [0, 1, 0, 1])   # 'noBack': 들어온 링크(좌)도 막음
        RL.maskMode = 'deadline'
        observed = obs_from_sim(1, 0, queue, G, P, RL, 43, 20)
        np.testing.assert_array_equal(observed.mask, [0, 1, 0, 1])   # 기한 안에 못 가는 방향(좌)도 막음
        self.assertFalse(observed.deadlineFallback)
        fallback = action_mask(observed.queueLengths, P, G, 1, 0, 1, 'deadline')
        self.assertTrue(fallback.deadlineFallback)
        self.assertGreater(fallback.values.sum(), 0)

    def test_history_observations(self):
        P = config_isl()
        RL = config_rl(P)
        RL.stateMode, RL.obsDim = 'full', 24   # 이전 State 24개 계산 확인 (기본은 coarse 15개)
        G = build_grid(P)
        hist = LinkHistory(G.numLinks)
        right = G.linkId[1, 0, 3]                         # (1, 0)에서 우 방향 링크
        queue = np.zeros(G.numLinks, dtype=int)
        for t in range(1, 21):                            # 우 방향 큐가 step마다 2개씩 참
            queue[right] = 2 * t
            hist.record(t, queue)
        hist.drop(right, 15)
        queue[right] = 42
        o = obs_from_sim(1, 0, queue, G, P, RL, 70, 20, hist, 21).values
        self.assertAlmostEqual(o[0 + 3], 42 / 200)            # 큐 길이
        self.assertAlmostEqual(o[8 + 3], (42 - 22) / 50)      # 큐 증가 속도: 지금 42, 10 step 전(11) 22
        self.assertAlmostEqual(o[12 + 3], 6 / 300)            # 최근 넘침: 6 step 전
        self.assertEqual(o[12 + 1], 1.0)                      # 넘친 적 없는 하 방향
        self.assertEqual(o[16 + 0], 0.0)                      # (1, 0)의 상 방향은 격자 끝
        self.assertEqual(o[16 + 3], 1.0)
        early = obs_from_sim(1, 0, queue, G, P, RL, 70, 20, hist, 5).values
        self.assertEqual(early[8 + 3], 0.0)                   # 시작 10 step 동안 증가 속도 0

    def test_agent_rejects_empty_nonterminal_action_mask(self):
        RL = config_rl(config_isl())
        RL.bufferSize = 2
        RL.batchSize = 1
        agent = DQNAgent(RL)
        obs = np.zeros(RL.obsDim, dtype=np.float32)
        empty = np.zeros(RL.numActions, dtype=np.float32)
        with self.assertRaisesRegex(ValueError, '행동 마스크'):
            agent.act(obs, empty)
        agent.remember(obs, 0, 0.0, obs, 0.0, empty)
        with self.assertRaisesRegex(ValueError, '다음 행동 마스크'):
            agent.learn()

    def test_coarse_observation(self):
        # 기본 State (coarse 15개, 11/20): 큐 3단계, 이웃 부하, 링크 유무, 남은 거리, 남은 기한
        P = config_isl()
        RL = config_rl(P)
        self.assertEqual((RL.stateMode, RL.obsDim, RL.maskMode, RL.rewardRiskQueue, RL.riskQueueLevel),
                         ('coarseTrend', 23, 'noBack', 0.5, 100))   # 기본값 (11/23 6차)
        RL.stateMode, RL.obsDim = 'coarseIn', 19                 # 이리듐 2차 모델 (+ 들어온 방향 4)
        G = build_grid(P)
        queue = np.zeros(G.numLinks, dtype=int)
        queue[G.linkId[1, 0, 3]] = 160                    # (1, 0) 우 방향 큐 160개 -> 혼잡 1
        queue[G.linkId[1, 0, 1]] = 120                    # 하 방향 큐 120개 -> 보통 0.5
        o = obs_from_sim(1, 0, queue, G, P, RL, 43, 20).values
        self.assertEqual(o.shape, (19,))
        self.assertEqual(list(o[:4]), [0.0, 0.5, 0.0, 1.0])
        self.assertEqual(list(o[8:12]), [0.0, 1.0, 1.0, 1.0])   # 상 방향은 격자 끝
        self.assertAlmostEqual(o[14], 43 / 70, places=5)
        self.assertEqual(list(o[15:]), [0, 0, 0, 0])             # 막 생성된 패킷: 들어온 방향 없음
        o = obs_from_sim(1, 0, queue, G, P, RL, 43, 20, backDir=3).values
        self.assertEqual(list(o[15:]), [0, 0, 1, 0])             # 왼쪽 위성에서 들어옴
        RL.stateMode, RL.obsDim = 'coarse', 15
        self.assertEqual(obs_from_sim(1, 0, queue, G, P, RL, 43, 20, backDir=3).values.shape, (15,))
        RL.stateMode, RL.obsDim = 'coarseTrend', 23              # + 큐 증가 속도 4, 최근 큐 넘침 4
        o = obs_from_sim(1, 0, queue, G, P, RL, 43, 20).values
        self.assertEqual(o.shape, (23,))
        self.assertEqual(list(o[19:]), [1.0, 1.0, 1.0, 1.0])     # 기록 없음: 넘친 적 없음
        G.dstSat = [5, 5]                                        # 남은 거리: 1칸 = 0.2, 5칸 넘으면 1로 자름 (망 크기와 상관없이)
        RL.normDist = 2                                          #   자르기 확인용 (기본 5)
        self.assertEqual(list(obs_from_sim(1, 0, queue, G, P, RL, 43, 20).values[12:14]), [1.0, 1.0])
        RL.normDist = 5
        from rl.rl_reward import hop_reward                       # 위험 링크 진입 벌점: 100개에서 0, 200개에서 0.5, 사이는 비례
        RL.rewardHopQueue = False
        for q, risk in [(50, 0), (100, 0), (150, 0.25), (200, 0.5)]:
            self.assertAlmostEqual(hop_reward(10, q, P, RL), -10 / RL.rewardHopScale - risk)

    def test_back_direction_in_sim(self):
        # 시뮬레이터가 패킷마다 들어온 방향을 넘겨 줌: 직전에 고른 방향의 반대
        from sim.run_isl_sim import OPPOSITE, ROUTE_FUNCS
        seen = []
        orig = ROUTE_FUNCS['routeB']

        def spy(p, s, queueLen, G, P, backDir=0, **kw):
            out = orig(p, s, queueLen, G, P, **kw)
            seen.append((kw.get('hops'), backDir, out[0]))
            return out
        P = config_isl()
        P.simTime, P.bgEnable, P.numFlows, P.routeName = 50, False, 1, 'routeB'
        ROUTE_FUNCS['routeB'] = spy
        try:
            run_isl_sim(P, P.genRate, 0, 1, False)
        finally:
            ROUTE_FUNCS['routeB'] = orig
        first = [x for x in seen if x[0] == 0]
        self.assertTrue(first and all(b == 0 for _, b, _ in first))   # 막 생성
        self.assertTrue(all(b in OPPOSITE for h, b, _ in seen if h > 0))


if __name__ == '__main__':
    unittest.main()
