
"""
External GSL packet interface for the Python ISL simulator.

Preserves original MATLAB packet IDs and timestamps.
Converts continuous ISL entry times into discrete simulation steps.

STEP 33: CSV loader only.
"""

from pathlib import Path
from numbers import Integral

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "packet_id",
    "generation_time_s",
    "isl_entry_time_s",
    "source_sat_id",
    "p_zero_based",
    "s_zero_based",
    "packet_size_bytes",
    "gsl_on_time",
    "gsl_delay_ms",
]

INTEGER_COLUMNS = [
    "packet_id",
    "source_sat_id",
    "p_zero_based",
    "s_zero_based",
    "packet_size_bytes",
    "gsl_on_time",
]

MAX_EXACT_INTEGER = 2**53


def _positive_integer(name, value):

    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, Integral)
        or value <= 0
    ):
        raise ValueError(
            f"{name} must be a positive integer"
        )

    return int(value)


def _positive_float(name, value):

    if isinstance(value, (bool, np.bool_)):
        raise ValueError(
            f"{name} must be a positive number"
        )

    value = float(value)

    if not np.isfinite(value) or value <= 0:
        raise ValueError(
            f"{name} must be a positive finite number"
        )

    return value


def load_external_packets(
    input_file,
    num_planes=6,
    sats_per_plane=11,
    step_time_s=0.001,
    duration_s=None,
    expected_packet_size=160,
):
    """
    Load and validate external GSL packets.

    Parameters
    ----------
    input_file : str or Path
        MATLAB common_packets.csv file.

    num_planes : int
        Number of orbital planes.

    sats_per_plane : int
        Number of satellites per plane.

    step_time_s : float
        ISL simulation step duration in seconds.

    duration_s : float or None
        Select packets generated before this time.
        None selects the complete CSV.

    expected_packet_size : int
        Packet size supported by the ISL simulation.

    Returns
    -------
    pandas.DataFrame
        Original nine common packet columns plus:

        internal_packet_id
        entry_step
        injection_time_s
        quantization_delay_ms

    Notes
    -----
    Original packet IDs are preserved.

    Internal packet IDs are contiguous and zero-based.

    Simulation step 1 represents time zero.

    Packets generated within the requested duration
    are retained even if their ISL entry occurs later.

    No destination, routing policy, deadline or TTL
    is assigned by this loader.
    """

    # 1. Validate simulation parameters

    num_planes = _positive_integer(
        "num_planes", num_planes
    )

    sats_per_plane = _positive_integer(
        "sats_per_plane", sats_per_plane
    )

    expected_packet_size = _positive_integer(
        "expected_packet_size",
        expected_packet_size
    )

    step_time_s = _positive_float(
        "step_time_s", step_time_s
    )

    if duration_s is not None:
        duration_s = _positive_float(
            "duration_s", duration_s
        )

    total_satellites = (
        num_planes * sats_per_plane
    )

    if total_satellites > MAX_EXACT_INTEGER:
        raise ValueError(
            "Invalid total satellite count"
        )

    # 2. Load CSV

    input_file = Path(input_file)

    if not input_file.is_file():
        raise FileNotFoundError(input_file)

    packets = pd.read_csv(input_file)

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in packets.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    packets = packets[
        REQUIRED_COLUMNS
    ].copy()

    # 3. Validate numeric data

    for col in REQUIRED_COLUMNS:

        packets[col] = pd.to_numeric(
            packets[col],
            errors="raise"
        )

    values = packets.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            "Invalid numeric data"
        )

    for col in INTEGER_COLUMNS:

        v = packets[col]

        if not (
            (v % 1 == 0)
            & (v.abs() <= MAX_EXACT_INTEGER)
        ).all():
            raise ValueError(
                f"Invalid integer column: {col}"
            )

        packets[col] = v.astype(np.int64)

    # 4. Validate original packet IDs

    if not packets["packet_id"].is_unique:
        raise ValueError(
            "Duplicate packet IDs"
        )

    if not (
        packets["packet_id"] >= 1
    ).all():
        raise ValueError(
            "Invalid packet IDs"
        )

    # 5. Validate timestamps

    if not (
        (packets["generation_time_s"] >= 0)
        & (
            packets["isl_entry_time_s"]
            >= packets["generation_time_s"]
        )
    ).all():
        raise ValueError(
            "Invalid timestamps"
        )

    # 6. Validate satellite coordinates

    if not packets["source_sat_id"].between(
        1, total_satellites
    ).all():
        raise ValueError(
            "Invalid satellite IDs"
        )

    if not (
        packets["p_zero_based"].between(
            0, num_planes - 1
        )
        & packets["s_zero_based"].between(
            0, sats_per_plane - 1
        )
    ).all():
        raise ValueError(
            "Invalid orbital indices"
        )

    expected_id = (
        packets["p_zero_based"]
        * sats_per_plane
        + packets["s_zero_based"]
        + 1
    )

    if not (
        packets["source_sat_id"]
        == expected_id
    ).all():
        raise ValueError(
            "Satellite ID mapping mismatch"
        )

    # 7. Validate packet size and GSL status

    if not (
        packets["packet_size_bytes"]
        == expected_packet_size
    ).all():
        raise ValueError(
            "Unexpected packet size"
        )

    if not packets["gsl_on_time"].isin(
        [0, 1]
    ).all():
        raise ValueError(
            "Invalid GSL status"
        )

    # 8. Validate GSL delay

    if not (
        packets["gsl_delay_ms"] >= 0
    ).all():
        raise ValueError(
            "Negative GSL delay"
        )

    expected_delay = (
        packets["isl_entry_time_s"]
        - packets["generation_time_s"]
    ) * 1000.0

    if not (
        np.abs(
            packets["gsl_delay_ms"]
            - expected_delay
        ) < 0.001
    ).all():
        raise ValueError(
            "GSL delay mismatch"
        )

    # 9. Select simulation duration

    if duration_s is not None:

        packets = packets.loc[
            packets["generation_time_s"]
            < duration_s
        ].copy()

    # 10. Preserve original packet sequence

    packets = packets.sort_values(
        "packet_id"
    ).reset_index(drop=True)

    packets["internal_packet_id"] = np.arange(
        len(packets),
        dtype=np.int64
    )

    # 11. Convert entry times into ISL steps

    entry_times = packets[
        "isl_entry_time_s"
    ].to_numpy(dtype=float)

    with np.errstate(over="ignore"):

        step_offsets = np.ceil(
            entry_times / step_time_s
        )

    if (
        not np.isfinite(step_offsets).all()
        or (
            step_offsets
            >= MAX_EXACT_INTEGER
        ).any()
    ):
        raise ValueError(
            "ISL entry step exceeds supported range"
        )

    step_offsets = step_offsets.astype(
        np.int64
    )

    injection_times = (
        step_offsets * step_time_s
    )

    # Protect against floating-point rounding
    # causing injection before actual arrival.

    early = injection_times < entry_times

    step_offsets[early] += 1

    injection_times = (
        step_offsets * step_time_s
    )

    packets["entry_step"] = (
        step_offsets + 1
    )

    packets["injection_time_s"] = (
        injection_times
    )

    packets["quantization_delay_ms"] = (
        injection_times - entry_times
    ) * 1000.0

    # 12. Validate discrete timestamps

    tolerance_ms = 1e-7

    quantization = packets[
        "quantization_delay_ms"
    ]

    if not (
        (quantization >= 0)
        & (
            quantization
            <= step_time_s * 1000.0
            + tolerance_ms
        )
    ).all():
        raise ValueError(
            "Invalid quantization delay"
        )

    # 13. Sort by injection schedule

    packets = packets.sort_values(
        [
            "entry_step",
            "isl_entry_time_s",
            "packet_id",
        ]
    ).reset_index(drop=True)

    return packets
