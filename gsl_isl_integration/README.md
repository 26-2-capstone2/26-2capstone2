# GSL-ISL Integrated Simulation

## 1. Overview

MATLAB GSL and Python ISL integration framework.

Current features:

- Original dynamic GSL integration

- Static GSL DDQN checkpoint restoration

- Multiple constellation sizes

- Common packet interface V2.0

- MATLAB-to-Python CSV exchange

- Python Mock ISL execution

- Integrated packet loss and latency analysis

- Consecutive packet loss and burst analysis

The original GSL algorithms, reward functions,

and trained DDQN checkpoints are preserved.

## 2. Requirements

- MATLAB with the toolboxes required by GSL

- Python 3

- NumPy

- pandas

Install Python dependencies from the repository root:

    python -m pip install -r gsl_isl_integration/requirements.txt

Tested Python version: 3.13.12

An alternative Python executable can be configured

using the GSL_ISL_PYTHON environment variable.

## 3. Run Static Integration

Open MATLAB and change the working directory

to the repository's gsl directory.

6 x 11 constellation:

    R6 = main_static_integrated_simulation(6,11,'DDQN',20282001);

20 x 20 constellation:

    R20 = main_static_integrated_simulation(20,20,'DDQN',20282001);

36 x 36 constellation:

    R36 = main_static_integrated_simulation(36,36,'DDQN',20282001);

Supported evaluation seeds:

    20282001 through 20282010

The current implementation uses the saved quadratic

DDQN checkpoints without additional training.

## 4. Simulation Configuration

- Duration: 600 seconds

- Packet generation rate: 60 packets/s

- Packet size: 160 bytes

- Generated packets per simulation: 36000

- Environment attenuation: 6 dB

- GSL policy: quadratic DDQN

- Q margin: 0.02

- ISL simulation mode: MOCK

- Mock ISL delay: 10 ms

## 5. Common Packet Interface

The common packet CSV contains nine columns:

- packet_id

- generation_time_s

- isl_entry_time_s

- source_sat_id

- p_zero_based

- s_zero_based

- packet_size_bytes

- gsl_on_time

- gsl_delay_ms

Satellite ID mapping:

    satellite_id = p * satsPerPlane + s + 1

The GSL receiving satellite becomes the ISL source

satellite for each successfully received packet.

## 6. Validation Results

Evaluation seed: 20282001

| Metric | 6x11 | 20x20 | 36x36 |
|---|---:|---:|---:|
| Satellites | 66 | 400 | 1296 |
| Visible satellites | 24 | 44 | 44 |
| Generated packets | 36000 | 36000 | 36000 |
| GSL received | 33681 | 34326 | 34411 |
| GSL lost | 2319 | 1674 | 1589 |
| Mock ISL lost | 0 | 0 | 0 |
| Total PLR (%) | 6.441667 | 4.650000 | 4.413889 |
| Delivery rate (%) | 93.558333 | 95.350000 | 95.586111 |
| Mean total delay (ms) | 13.779838 | 13.760561 | 13.731146 |
| Maximum consecutive loss | 68 | 33 | 76 |
| Burst count (>=2) | 361 | 255 | 240 |
| Burst count (>=3) | 251 | 188 | 170 |
| Handovers | 148 | 142 | 114 |
| Reference validation | PASS | PASS | PASS |

All 33 original GSL metric comparisons passed.

No additional DDQN training was performed.

No additional packet loss occurred during

the common interface and Mock ISL integration.

Validation CSV files:

    validation/static_ddqn_mock/

## 7. Generated Output Files

Each execution generates:

- common_packets.csv

- isl_result.csv

- gsl_all_packets.csv

- gsl_decisions.csv

- static_satellites.csv

- gsl_reference_comparison.csv

- overall_packets.csv

- overall_loss_runs.csv

- integrated_summary.csv

Generated outputs are stored under results/

and excluded from Git tracking.

## 8. Current Limitations

- ISL is currently a mock implementation.

- Mock ISL uses a fixed 10 ms delay.

- Real Dijkstra, DRA and DDQN routing are not connected.

- Static integration currently supports DDQN only.

- End-to-end deadline compliance is not yet evaluated.

- The reported validation results use one evaluation seed.

- Zero-received-packet scenarios are not supported

  by the current static integration function.

- The original training PHY curve file identity

  has not been independently verified.

These results validate the integration interface,

not actual ISL routing performance.

## 9. Next Development Stage

- Integrate the actual Python ISL simulator.

- Inject external GSL packets into the ISL simulator.

- Support packet-specific source satellites.

- Preserve original packet IDs and arrival timestamps.

- Connect Dijkstra, DRA and DDQN routing.

- Evaluate end-to-end latency and burst packet loss.

- Compare multiple constellation sizes and evaluation seeds.
