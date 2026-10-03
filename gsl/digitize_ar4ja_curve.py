"""Reproduce the committed table from the publisher PDF, not guessed values.
Usage: python digitize_ar4ja_curve.py /path/to/184D.pdf
Requires pdfplumber. No PDF is redistributed in this repository.
"""
import csv
import hashlib
import sys
from pathlib import Path
import pdfplumber

EXPECTED_SHA256 = "c2be196e7c5110f81b9b930b1d347be1e41dc89b4dbc16cc94f0d7f39d0708d4"
source = Path(sys.argv[1])
assert hashlib.sha256(source.read_bytes()).hexdigest() == EXPECTED_SHA256, "Source PDF changed; inspect it first"
with pdfplumber.open(source) as doc:
    page = doc.pages[29]  # printed page 30, Figure 14 (upper graph)
    # Dashed blue = rate 1/2 CWER; rightmost blue = k=1024.
    candidates = [p for p in page.curves if p['stroking_color'] == (0, 0, 1)
                  and p['dash'][0] and p['top'] < 100 and p['bottom'] < 330]
    # Different pdfplumber versions may use lists instead of tuples.
    if not candidates:
        candidates = [p for p in page.curves if list(p['stroking_color']) == [0, 0, 1]
                      and p['dash'][0] and p['top'] < 100 and p['bottom'] < 330]
    assert len(candidates) == 3
    target = max(candidates, key=lambda p: p['x1'])
    assert len(target['pts']) == 22
    rows = []
    for x, y in target['pts']:
        eb = 5 * (x - 172.951) / (516.751 - 172.951)
        cw = 10 ** (-8 * (y - 94.874) / (327.074 - 94.874))
        if abs(eb) < 1e-12:
            eb = 0.0
        rows.append([eb, min(1.0, cw), x, y])
output = Path(__file__).with_name('ar4ja_r12_k1024_cwer.csv')
with output.open('w', newline='', encoding='utf-8') as f:
    f.write('ebNo_dB,codewordErrorRate,pdfX_pt,pdfY_pt\n')
    for row in rows:
        f.write(','.join(format(v, '.12g') for v in row) + '\n')
print('Extracted 22 verified vector vertices:', output)
