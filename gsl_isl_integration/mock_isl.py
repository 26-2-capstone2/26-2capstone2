
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

MOCK_ISL_DELAY_MS = 10.0


def run_mock_isl(input_file, output_file):

    # 1. Load GSL packets
    packets = pd.read_csv(input_file)

    required_columns = [
        "packet_id",
        "generation_time_s",
        "isl_entry_time_s",
        "source_sat_id",
        "p_zero_based",
        "s_zero_based",
        "packet_size_bytes",
        "gsl_on_time",
        "gsl_delay_ms"
    ]

    missing = [
        col for col in required_columns
        if col not in packets.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # 2. Validate numeric data
    values = packets[required_columns].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError("Invalid numeric data")

    if not packets["packet_id"].is_unique:
        raise ValueError("Duplicate packet IDs")

    if not (
        (packets["packet_id"] >= 1) &
        (packets["packet_id"] % 1 == 0)
    ).all():
        raise ValueError("Invalid packet IDs")

    # 3. Validate timestamps
    if not (
        (packets["generation_time_s"] >= 0) &
        (packets["isl_entry_time_s"] >=
         packets["generation_time_s"])
    ).all():
        raise ValueError("Invalid timestamps")

    # 4. Validate satellite IDs
    if not (
        packets["source_sat_id"].between(1, 66) &
        (packets["source_sat_id"] % 1 == 0)
    ).all():
        raise ValueError("Invalid satellite IDs")

    if not (
        packets["p_zero_based"].between(0, 5) &
        (packets["p_zero_based"] % 1 == 0) &
        packets["s_zero_based"].between(0, 10) &
        (packets["s_zero_based"] % 1 == 0)
    ).all():
        raise ValueError("Invalid orbital indices")

    expected_id = (
        packets["p_zero_based"] * 11
        + packets["s_zero_based"] + 1
    )

    if not (packets["source_sat_id"] == expected_id).all():
        raise ValueError("Satellite ID mapping mismatch")

    # 5. Validate packet size and GSL status
    if not (
        (packets["packet_size_bytes"] > 0) &
        (packets["packet_size_bytes"] % 1 == 0)
    ).all():
        raise ValueError("Invalid packet size")

    if not packets["gsl_on_time"].isin([0, 1]).all():
        raise ValueError("Invalid GSL status")

    expected_delay = (
        packets["isl_entry_time_s"]
        - packets["generation_time_s"]
    ) * 1000.0

    if not np.allclose(
        packets["gsl_delay_ms"],
        expected_delay,
        atol=0.001,
        rtol=0
    ):
        raise ValueError("GSL delay mismatch")

    # 6. Sort packets
    packets = packets.sort_values(
        ["isl_entry_time_s", "packet_id"]
    ).reset_index(drop=True)

    # 7. Mock ISL processing
    result = packets.copy()

    result["isl_delivered"] = 1
    result["isl_delay_ms"] = MOCK_ISL_DELAY_MS

    result["isl_exit_time_s"] = (
        result["isl_entry_time_s"]
        + result["isl_delay_ms"] / 1000.0
    )

    result["total_delay_ms"] = (
        result["isl_exit_time_s"]
        - result["generation_time_s"]
    ) * 1000.0

    result["isl_drop_reason"] = "NONE"
    result["simulation_mode"] = "MOCK"

    # 8. Verify output
    if len(result) != len(packets):
        raise ValueError("Packet count mismatch")

    if not result["packet_id"].equals(
        packets["packet_id"]
    ):
        raise ValueError("Packet ID mismatch")

    # 9. Export results
    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(output_file, index=False)

    # 10. Print summary
    print("\n===== MOCK ISL RESULT =====")
    print(f"Input packets: {len(packets)}")
    print(f"Output packets: {len(result)}")
    print(f"Delivered packets: {result['isl_delivered'].sum()}")
    print("Packet ID validation: PASS")
    print("Timestamp validation: PASS")
    print("Satellite ID validation: PASS")
    print("GSL delay validation: PASS")
    print(f"Mock ISL editdelay: {MOCK_ISL_DELAY_MS} ms")
    print(f"Output file: {output_file}")
    print("Simulation mode: MOCK")
    print("===========================")

    return result


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    run_mock_isl(args.input, args.output)

 