"""연속 손실 정의, 종료 순서, 기한 행동 마스크의 회귀 테스트."""

import unittest
import numpy as np

from analysis.burst_summary import burst_summary
from config_isl import config_isl
from rl.config_rl import config_rl
from rl.rl_agent import DQNAgent
from rl.rl_collector import Collector
from rl.rl_state import action_mask, obs_from_log, obs_from_sim
from sim.build_grid import build_grid


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

    def test_terminal_reward_waits_for_out_of_order_packets(self):
        P = config_isl()
        RL = config_rl(P)
        agent = FakeAgent()
        collector = Collector(agent, P, RL)
        mask = np.ones(4, dtype=np.float32)
        status = np.zeros(4, dtype=int)
        for packet_id in range(4):
            obs = np.full(RL.obsDim, packet_id, dtype=np.float32)
            collector.on_decision(packet_id, (obs, mask, 0), 0, True)
        for packet_id in (3, 2, 1, 0):
            status[packet_id] = 4
            collector.on_end([packet_id], status)
        self.assertEqual(collector.numBurstPenalties, 2)
        self.assertEqual(collector.finish(), 0)
        terminal_rewards = {int(t[0][0]): t[2] for t in agent.transitions}
        hop = -P.linkDelay[0] / P.deadline
        self.assertAlmostEqual(terminal_rewards[0], hop - 1)
        self.assertAlmostEqual(terminal_rewards[1], hop - 1)
        self.assertAlmostEqual(terminal_rewards[2], hop - 1 - RL.consecPenalty)
        self.assertAlmostEqual(terminal_rewards[3], hop - 1 - RL.consecPenalty)

    def test_success_breaks_burst_even_if_packets_finish_out_of_order(self):
        P = config_isl()
        RL = config_rl(P)
        agent = FakeAgent()
        collector = Collector(agent, P, RL)
        mask = np.ones(4, dtype=np.float32)
        status = np.zeros(3, dtype=int)
        for packet_id in range(3):
            obs = np.full(RL.obsDim, packet_id, dtype=np.float32)
            collector.on_decision(packet_id, (obs, mask, 0), 0, True)
        for packet_id, result in ((2, 4), (1, 4), (0, 1)):
            status[packet_id] = result
            collector.on_end([packet_id], status)
        self.assertEqual(collector.numBurstPenalties, 0)
        self.assertEqual(collector.finish(), 0)

    def test_deadline_mask_matches_live_and_logged_observations(self):
        P = config_isl()
        RL = config_rl(P)
        G = build_grid(P)
        queue = np.zeros(G.numLinks, dtype=int)
        observed = obs_from_sim(1, 0, queue, G, P, RL, 43, 20)
        np.testing.assert_array_equal(observed.mask, [0, 1, 0, 1])
        self.assertFalse(observed.deadlineFallback)
        row = np.zeros(24)
        row[3:5] = [1, 0]
        row[5:9], row[9:13], row[13:17] = observed.queueLengths, observed.linkLoads, observed.neighborLoads
        row[17:21] = [4, 5, 43, 20]
        log_obs, log_mask = obs_from_log(row, P, RL)
        np.testing.assert_array_equal(log_mask[0], observed.mask)
        np.testing.assert_array_equal(log_obs[0], observed.values)
        fallback = action_mask(observed.queueLengths, P, G, 1, 0, 1)
        self.assertTrue(fallback.deadlineFallback)
        self.assertGreater(fallback.values.sum(), 0)

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


if __name__ == '__main__':
    unittest.main()
