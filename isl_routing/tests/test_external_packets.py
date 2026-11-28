
"""
Unit tests for the external GSL packet CSV loader.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from sim.external_packets import (
    REQUIRED_COLUMNS,
    load_external_packets,
)


class ExternalPacketTest(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(
            self.temp_dir.cleanup
        )

        self.path = (
            Path(self.temp_dir.name)
            / "common_packets.csv"
        )

        self.data = pd.DataFrame(
            [
                [
                    1, 0.0, 0.0035,
                    23, 2, 0, 160, 1, 3.5
                ],
                [
                    3, 0.02, 0.024,
                    34, 3, 0, 160, 1, 4.0
                ],
                [
                    5, 0.04, 0.0432,
                    45, 4, 0, 160, 1, 3.2
                ],
            ],
            columns=REQUIRED_COLUMNS
        )

    def load(self, data=None, **kwargs):

        if data is None:
            data = self.data

        data.to_csv(
            self.path,
            index=False
        )

        return load_external_packets(
            self.path,
            **kwargs
        )

    def test_valid_packets(self):

        result = self.load()

        self.assertEqual(len(result), 3)

        self.assertEqual(
            result.packet_id.tolist(),
            [1, 3, 5]
        )

        self.assertEqual(
            result.internal_packet_id.tolist(),
            [0, 1, 2]
        )

        self.assertEqual(
            result.entry_step.tolist(),
            [5, 25, 45]
        )

        self.assertTrue(
            (
                result.injection_time_s
                >= result.isl_entry_time_s
            ).all()
        )

    def test_quantization_delay(self):

        result = self.load()

        np.testing.assert_allclose(
            result.quantization_delay_ms,
            [0.5, 0.0, 0.8],
            atol=1e-8
        )

    def test_sorting(self):

        data = self.data.iloc[
            [2, 0, 1]
        ].copy()

        result = self.load(data)

        self.assertEqual(
            result.packet_id.tolist(),
            [1, 3, 5]
        )

    def test_out_of_order_arrival(self):

        data = self.data.copy()

        data.loc[0, "isl_entry_time_s"] = 0.030
        data.loc[0, "gsl_delay_ms"] = 30.0
        data.loc[0, "gsl_on_time"] = 0

        result = self.load(data)

        self.assertEqual(
            result.packet_id.tolist(),
            [3, 1, 5]
        )

        self.assertEqual(
            result.internal_packet_id.tolist(),
            [1, 0, 2]
        )

    def test_duration_filter(self):

        result = self.load(
            duration_s=0.03
        )

        self.assertEqual(
            result.packet_id.tolist(),
            [1, 3]
        )

    def test_boundary_packet_preserved(self):

        result = self.load(
            duration_s=0.021
        )

        self.assertEqual(len(result), 2)

        self.assertGreater(
            result.iloc[-1].isl_entry_time_s,
            0.021
        )

    def test_empty_input(self):

        result = self.load(
            self.data.iloc[0:0]
        )

        self.assertEqual(len(result), 0)

        self.assertIn(
            "entry_step",
            result.columns
        )

        self.assertIn(
            "internal_packet_id",
            result.columns
        )

    def test_missing_column(self):

        data = self.data.drop(
            columns=["packet_id"]
        )

        with self.assertRaises(ValueError):
            self.load(data)

    def test_duplicate_packet_id(self):

        data = self.data.copy()

        data.loc[1, "packet_id"] = 1

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_packet_id(self):

        data = self.data.copy()

        data.loc[0, "packet_id"] = 0

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_timestamp(self):

        data = self.data.copy()

        data.loc[1, "isl_entry_time_s"] = 0.01

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_satellite_id(self):

        data = self.data.copy()

        data.loc[0, "source_sat_id"] = 67

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_coordinates(self):

        data = self.data.copy()

        data.loc[0, "p_zero_based"] = 6

        with self.assertRaises(ValueError):
            self.load(data)

    def test_satellite_mapping_mismatch(self):

        data = self.data.copy()

        data.loc[0, "source_sat_id"] = 24

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_packet_size(self):

        data = self.data.copy()

        data.loc[0, "packet_size_bytes"] = 128

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_gsl_status(self):

        data = self.data.copy()

        data.loc[0, "gsl_on_time"] = 2

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_gsl_delay(self):

        data = self.data.copy()

        data.loc[0, "gsl_delay_ms"] = 9.0

        with self.assertRaises(ValueError):
            self.load(data)

    def test_nonfinite_data(self):

        data = self.data.copy()

        data.loc[0, "gsl_delay_ms"] = np.inf

        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_configuration(self):

        for kwargs in [
            {"num_planes": 0},
            {"sats_per_plane": -1},
            {"step_time_s": 0},
            {"duration_s": -10},
            {"expected_packet_size": 0},
        ]:

            with self.subTest(kwargs=kwargs):

                with self.assertRaises(ValueError):
                    self.load(**kwargs)

    def test_multiple_constellation_sizes(self):

        for planes, sats in [
            (6, 11),
            (20, 20),
            (36, 36),
        ]:

            with self.subTest(
                planes=planes,
                sats=sats
            ):

                data = self.data.copy()

                data["source_sat_id"] = (
                    data["p_zero_based"] * sats
                    + data["s_zero_based"]
                    + 1
                )

                result = self.load(
                    data,
                    num_planes=planes,
                    sats_per_plane=sats
                )

                self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
