# AR4JA CWER lookup provenance

Source: [Jon Hamkins, Performance of Low-Density Parity-Check Coded Modulation, JPL IPN Progress Report 42-184, 15 February 2011](https://ipnpr.jpl.nasa.gov/progress_report/42-184/184D.pdf).

Target: Figure 14, printed/PDF page 30, upper graph; dashed blue rate 1/2 CWER, **rightmost of the three blue dashed curves**, information k=1024. Solid curves are BER and are not used. The source caption covers coded BPSK/QPSK; we use its Gray QPSK AWGN result, not the removed uncoded reference model.

Source PDF SHA-256: c2be196e7c5110f81b9b930b1d347be1e41dc89b4dbc16cc94f0d7f39d0708d4

## Extraction

The publisher PDF contains vector polylines. pdfplumber reads the 22 vertices of the selected curve. [digitize_ar4ja_curve.py](digitize_ar4ja_curve.py) reproduces [ar4ja_r12_k1024_cwer.csv](ar4ja_r12_k1024_cwer.csv) and verifies the source hash. Download the linked PDF outside the source folder before running the script.

Figure 14 axes in PDF points, top-left page coordinates:

- x=172.951 → 0 dB; x=516.751 → 5 dB.
- y=94.874 → CWER 1; y=327.074 → CWER 1e-8.
- Eb/N0 =5*(x-172.951)/(516.751-172.951).
- log10(CWER) =-8*(y-94.874)/(327.074-94.874).

CSV contains Eb/N0, CWER and original PDF x/y, retaining 12 significant digits for reproducibility, not implying Monte Carlo precision. PDF vertex quantization is approximately 0.00065 dB horizontally and 0.00155 decade vertically; source simulation statistical uncertainty is additional and cannot be recovered from the graph alone.

getPERfromSNR interpolates log10(CWER) linearly between these vertices, following the semilog polyline. Support is 0..2.2002617801 dB with the final sampled CWER approximately 1.7083e-7. No additional points, extrapolation, endpoint clamping or assumed zero high-SNR loss. The curve is an approximate reconstruction of the plotted result, not original raw simulation observations.

## Decoder / applicability

See JPL §VI.A and preceding optimized decoder sections for exact LLR, quantization and iteration conditions. A different receiver/decoder may change CWER. The simulator does not run an AR4JA encoder/decoder itself. Packet approximation uses two independent k=1024 information blocks for 1280 bits: PER=1-(1-CWER)^2.

## Mapping TODO

The current density-based SNR is C/N. Use Eb/N0=C/N+10log10(Bnoise/Rinformation), with bandwidth Hz and information bit rate bit/s. The project has no confirmed absolute receiver noise bandwidth or documented interpretation of its 50 Mbps link rate. Reference A Table 2 does not supply that bandwidth; its body and table also differ on downlink speed. Therefore defaults stay NaN. CFG.phyMappingSource must document both values before finite mapping is accepted. Curve-range violations remain unresolved even after bandwidth is supplied.
