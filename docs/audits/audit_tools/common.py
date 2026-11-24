"""Audit-only I/O and independent scalar oracles; never write pipeline outputs."""
from pathlib import Path
import csv
import hashlib
import json
import math
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATA = Path('D:/TuNam4/dataset_HF_CFD_final')
EVIDENCE = ROOT / 'docs/audits/evidence'
sys.path.insert(0, str(ROOT))


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def dump(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False,
        allow_nan=False, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)), encoding='utf-8')


def csv_out(name, rows):
    if not rows:
        return
    with (EVIDENCE / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scalar_a2(p, epsilon=1e-8):
    """Equations audited separately from anatomical endpoint validity.

    Python scalar double arithmetic, no call to the A implementation.
    Indices explicitly document the implementation's 0-based mapping.
    """
    p = [[float(x), float(y)] for x, y in p]
    dist = lambda a, b: math.hypot(a[0]-b[0], a[1]-b[1])
    avg = lambda indices: [math.fsum(p[i][j] for i in indices)/len(indices) for j in (0, 1)]
    el, er = avg(list(range(36, 42))), avg(list(range(42, 48)))
    ec = [(el[j]+er[j])/2 for j in (0, 1)]
    brow = [(p[21][j]+p[22][j])/2 for j in (0, 1)]
    fh, ipd = dist(brow, p[8]), dist(el, er)
    ew_l, ew_r = dist(p[36], p[39]), dist(p[42], p[45])
    mouth = [(p[48][j]+p[54][j])/2 for j in (0, 1)]
    u = [p[4][j]-p[8][j] for j in (0, 1)]
    v = [p[12][j]-p[8][j] for j in (0, 1)]
    values = [(dist(p[2], p[14]), fh), (ipd, fh), (ew_l, ipd), (ew_r, ipd),
              (dist(p[37], p[41])+dist(p[38], p[40]), 2*ew_l),
              (dist(p[43], p[47])+dist(p[44], p[46]), 2*ew_r),
              (dist(p[31], p[35]), ipd), (dist(p[48], p[54]), ipd),
              (dist(p[62], p[66]), ipd), (dist(ec, p[30]), ipd),
              (dist(ec, mouth), ipd), (dist(p[30], p[8]), fh), (dist(p[4], p[12]), fh)]
    angle = math.degrees(math.acos(max(-1., min(1., math.fsum(a*b for a, b in zip(u, v)) /
                                      (math.hypot(*u)*math.hypot(*v))))))
    return [num/(den+epsilon) for num, den in values]+[angle], values+[(angle, 1.)], (el, er, ec, ipd)


def scalar_color(image, mask):
    """Independent bin assignment + fsum moment/circular equations.

    OpenCV is reused only for the approved color conversion, not histograms,
    descriptor, fitting, transform, or retrieval routines under audit.
    """
    import cv2
    pixels = image[np.asarray(mask) > 0]
    if len(pixels) < 100:
        return None
    strip = pixels.reshape(-1, 1, 3)
    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    lab = cv2.cvtColor(strip.astype(np.float32)/255, cv2.COLOR_BGR2LAB).reshape(-1, 3)
    bins = (hsv[:, 0].astype(int)//15)*4 + hsv[:, 1].astype(int)//64
    hs = np.bincount(bins, minlength=48)/len(pixels)
    hh = np.bincount(hsv[:, 0].astype(int)//18, minlength=10)/len(pixels)
    moments = []
    for channel in lab.T:
        n = len(channel)
        mu = math.fsum(map(float, channel))/n
        centered = [float(x)-mu for x in channel]
        variance = math.fsum(x*x for x in centered)/n
        sd = math.sqrt(variance)
        skew = math.fsum(x**3 for x in centered)/n/sd**3 if sd >= 1e-12 else 0.
        kurt = math.fsum(x**4 for x in centered)/n/sd**4 if sd >= 1e-12 else 0.
        moments.extend([mu, sd if sd >= 1e-12 else 0., skew, kurt])
    angles = [2*math.pi*float(h)/180 for h in hsv[:, 0]]
    c, s = math.fsum(map(math.cos, angles))/len(angles), math.fsum(map(math.sin, angles))/len(angles)
    r = max(0., min(1., math.hypot(c, s)))
    angle = math.atan2(s, c) % (2*math.pi)
    if abs(angle-2*math.pi) <= 1e-12:
        angle = 0.
    mean = angle/(2*math.pi) if r >= 1e-8 else 0.
    std = min(math.sqrt(-2*math.log(max(r, 1e-12)))/(2*math.pi), 1.)
    return np.r_[hs, moments, hh, mean, std]
