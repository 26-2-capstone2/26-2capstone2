# Week 6 GSL PHY update

Modified `configGSL.m`, `getPERfromSNR.m`, and `verify_packets.m`.

- Common traffic: 600 s, 160 bytes, 60 packets/s (unchanged).
- Reference PHY assumption: 50 Mbps information bit rate, 50 MHz noise/occupied bandwidth, ideal Nyquist QPSK + AR4JA rate 1/2. These are NOT measured Starlink bandwidth or information rate.
- SNR to Eb/N0 conversion uses B/Rb=1 under this assumption.
- JPL IPN Progress Report 42-184 Article 184D Figure 14: digitized CWER is interpolated in log10 space inside the table only.
- Above the digitized curve, the optional `ZERO_OBSERVABLE_ERRORS` policy sets simulated CWER/PER to zero and marks `HIGH_SNR_BELOW_RESOLUTION`. This is a finite-run modeling approximation, NOT a claim of zero physical error probability.
- Below the curve remains unresolved (NaN), not falsely counted as success.
- 160 B is modeled as two independent 1024-information-bit codewords.

## Verification
Updated verification separates missing-bandwidth fixtures, strict no-extrapolation tests, and the labeled high-SNR baseline approximation.
Run `verify_packets` and `main_gsl_simulation` in MATLAB with the `gsl` directory selected as Current Folder. No MATLAB execution was available during this patch; output metrics have not been verified.

## Caveat
A conservative upper-end CWER approximation or sensitivity tests should be added for research conclusions that depend on very rare PHY errors. The high-SNR baseline approximation must be disclosed in reporting.
