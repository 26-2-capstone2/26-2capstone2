# 주 흐름 여러 개 (sim/flows.py) 확인
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.burst_summary import loss_run_lengths
from config_isl import apply_bg_level, config_isl
from routing.route_A import _dist_to
from sim.bg_traffic import sample_hotspots
from sim.build_grid import build_grid
from sim.flows import make_flows
from sim.run_isl_sim import run_isl_sim


class MultiFlowTest(unittest.TestCase):
    def setUp(self):
        self.P = config_isl()
        self.P.numFlows = 3
        self.G = build_grid(self.P)

    def test_flows(self):
        # 흐름 0은 기존 주 흐름, 나머지는 최소 지연 조건을 만족하고 서로 다름, 같은 시드면 같은 흐름
        flows = make_flows(self.P, self.G, 11)
        self.assertEqual(len(flows), 3)
        self.assertEqual(flows[0], ((0, 0), (5, 5)))
        self.assertEqual(len(set(flows)), 3)
        for src, dst in flows[1:]:
            d = _dist_to(self.G, dst)[src]
            self.assertTrue(self.P.flowDelayMin <= d <= self.P.flowDelayMax)
        self.assertEqual(flows, make_flows(self.P, self.G, 11))
        self.P.numFlows = 1
        self.assertEqual(make_flows(self.P, self.G, 11), [((0, 0), (5, 5))])

    def test_burst_split_by_flow(self):
        # 흐름 0의 마지막 손실 2개와 흐름 1의 첫 손실 2개는 이어지지 않음 (각각 길이 2)
        status = np.array([1, 1, 4, 4, 4, 4, 1, 1])
        flow = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        self.assertEqual(sorted(loss_run_lengths(status, flow).tolist()), [2, 2])

    def test_sim_three_flows(self):
        # 흐름마다 같은 수의 패킷, 패킷 id는 흐름별 묶음, 모든 패킷이 끝남
        P = self.P
        apply_bg_level(P, 'high')
        P.simTime = 1000
        P.routeName = 'routeB'
        sample_hotspots(P, self.G, 3)
        R = run_isl_sim(P, P.genRate, 0, 3, False)
        self.assertEqual(R.numFlows, 3)
        self.assertEqual(np.bincount(R.packetFlow).tolist(), [60, 60, 60])
        self.assertTrue(np.all(np.diff(R.packetFlow) >= 0))
        self.assertTrue(np.all(R.status > 0))

    def test_link_failures(self):
        # extreme: 장애가 생기고, 끊긴 순간에도 모든 흐름에 길이 남고, 시뮬레이션이 끝까지 돎
        from sim.bg_traffic import path_exists
        P = self.P
        apply_bg_level(P, 'extreme')
        P.simTime = 3000
        P.routeName = 'routeB'
        P.flowZeroRandom = True
        sample_hotspots(P, self.G, 5)
        self.assertTrue(len(P.failEvents) > 0)
        self.assertNotEqual(P.mainFlows[0], ((0, 0), (5, 5)))
        for a, b, cut in P.failEvents:
            down = set().union(*[c for x, y, c in P.failEvents if x <= a <= y])
            for src, dst in P.mainFlows:
                self.assertTrue(path_exists(P, self.G, src, dst, down))
        R = run_isl_sim(P, P.genRate, 0, 5, False)
        self.assertTrue(np.all(R.status > 0))
        apply_bg_level(P, 'severe')
        self.assertFalse(P.failEnable)
        self.assertEqual((P.evLoadMin, P.evLoadMax, P.evNbrRatio), (0.5, 1.5, 0.5))


if __name__ == '__main__':
    unittest.main()
