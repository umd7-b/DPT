"""EXPERIMENTAL_TECHNICAL_TRIAL; ROI_ANATOMY_STATUS=PROVISIONAL.

Pinned C1 arithmetic. No detector, fitting, database writes or retrieval ranking.
Landmarks are pixel xy in the already aligned image, not new alignment evidence.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = ROOT / 'outputs/C1_lbp/roi_validation'
ROI_HASH = '61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c'
SPEC_HASH = '7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851'
REGIONS = ('forehead_brow', 'cheek_left_viewer', 'cheek_right_viewer', 'nose_mouth')
LABEL = 'EXPERIMENTAL_TECHNICAL_TRIAL'
ANATOMY = 'PROVISIONAL'
SQRT2 = math.sqrt(2.0)
OFFSETS = ((2., 0.), (SQRT2, -SQRT2), (0., -2.), (-SQRT2, -SQRT2),
           (-2., 0.), (-SQRT2, SQRT2), (0., 2.), (SQRT2, SQRT2))
SUPPORT = tuple(sorted({(0, 0)} | {(x, y) for dx, dy in OFFSETS
                      for x in {math.floor(dx), math.ceil(dx)}
                      for y in {math.floor(dy), math.ceil(dy)}}, key=lambda xy: (xy[1], xy[0])))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def content_hash(value):
    value = {k: v for k, v in value.items() if k != 'content_sha256'}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


class Context:
    """Load the immutable trial definitions; mismatch is fatal, never repaired."""
    def __init__(self, spec_dir=SPEC_DIR):
        spec_dir = Path(spec_dir)
        self.roi = json.loads((spec_dir / 'contract_v0_2.json').read_text(encoding='utf-8'))
        self.spec = json.loads((spec_dir / 'lbp_implementation_spec.json').read_text(encoding='utf-8'))
        for obj, expected, schema in (
            (self.roi, ROI_HASH, 'C1_ROI_RAW_CONTRACT_v0.2.0'),
            (self.spec, SPEC_HASH, 'C1_LBP_236_IMPLEMENTATION_SPEC_v0.1.0')):
            if obj.get('schema_id') != schema or obj.get('content_sha256') != expected or content_hash(obj) != expected:
                raise ValueError('Pinned schema/content hash mismatch: ' + schema)
        if (self.spec['roi_contract_content_sha256'] != ROI_HASH
                or self.spec['roi_contract_file_sha256'] != sha256(spec_dir / 'contract_v0_2.json')):
            raise ValueError('Spec links to a different ROI contract file')
        if tuple(self.roi['region_order']) != REGIONS or self.spec['conventions']['support_footprint_xy'] != [list(p) for p in SUPPORT]:
            raise ValueError('Unexpected region order or support footprint')
        with (spec_dir / 'nri_uniform_59_codebook.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.codebook = np.empty(256, np.uint8)
        if len(rows) != 256 or {int(r['raw_code']) for r in rows} != set(range(256)):
            raise ValueError('Invalid codebook domain')
        for row in rows:
            word, label = int(row['raw_code']), int(row['nri_uniform_bin'])
            bits = [(word >> p) & 1 for p in range(8)]
            transitions = sum(bits[p] != bits[(p + 1) % 8] for p in range(8))
            ones = sum(bits)
            if transitions > 2:
                expected = 58
            elif ones in (0, 8):
                expected = 0 if ones == 0 else 57
            else:
                start = next(p for p in range(8) if bits[p] and not bits[(p - 1) % 8])
                expected = 1 + 8 * (ones - 1) + ((-start) % 8)
            if label != expected:
                raise ValueError('Codebook differs from pinned bin convention')
            self.codebook[word] = label
        self.codebook.flags.writeable = False
        self.lock = dict(roi_contract_hash=ROI_HASH, lbp_spec_hash=SPEC_HASH,
                         codebook_file_sha256=sha256(spec_dir / 'nri_uniform_59_codebook.csv'),
                         trial_status=LABEL, ROI_ANATOMY_STATUS=ANATOMY)

    def require_lock(self, lock):
        if any(lock.get(k) != v for k, v in self.lock.items()):
            raise ValueError('Query/gallery contract/spec/codebook/status mismatch')

    def polygons(self, points):
        if points is None or points.shape != (478, 2) or points.dtype != np.float32 or not np.isfinite(points).all():
            raise ValueError('Missing/invalid float32 pixel landmarks478')
        left = points[[33, 160, 158, 133, 153, 144]].mean(axis=0).astype(np.float64)
        right = points[[362, 385, 387, 263, 373, 380]].mean(axis=0).astype(np.float64)
        distance = float(np.linalg.norm(right - left))
        if distance < 1e-6:
            raise ValueError('Degenerate eye frame')
        u = (right - left) / distance
        v = np.array([-u[1], u[0]], dtype=np.float64)
        if u[0] <= 0 or v[1] <= 0:
            raise ValueError('Unexpected eye orientation; no automatic swap')
        return {name: np.array([points[item['mediapipe_index']].astype(np.float64)
                                + distance * (item['offset_u_ipd'] * u + item['offset_v_ipd'] * v)
                                for item in self.roi['polygons'][name]]) for name in REGIONS}


def grayscale(bgr):
    if bgr.dtype != np.uint8 or bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError('Expected uint8 BGR image')
    color = bgr.astype(np.uint32)
    gray = (1868 * color[..., 0] + 9617 * color[..., 1] + 4899 * color[..., 2] + 8192) // 16384
    return gray.astype(np.uint8).astype(np.float64)


def geometry_error(vertices):
    if vertices is None:
        return 'missing_region'
    if vertices.ndim != 2 or vertices.shape[1] != 2 or len(vertices) < 3 or not np.isfinite(vertices).all():
        return 'invalid_vertices'
    n = len(vertices)
    if any(np.linalg.norm(vertices[i] - vertices[(i + 1) % n]) < 1e-9 for i in range(n)):
        return 'zero_edge'

    def cross(a, b, c):
        x, y = b - a
        z, w = c - a
        return x * w - y * z

    def touches(a, b, c):
        return (abs(cross(a, b, c)) <= 1e-9 and np.all(c >= np.minimum(a, b) - 1e-9)
                and np.all(c <= np.maximum(a, b) + 1e-9))

    for i in range(n):
        a, b = vertices[i], vertices[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            c, d = vertices[j], vertices[(j + 1) % n]
            if (cross(a, b, c) * cross(a, b, d) < -1e-9 and cross(c, d, a) * cross(c, d, b) < -1e-9
                    or touches(a, b, c) or touches(a, b, d) or touches(c, d, a) or touches(c, d, b)):
                return 'self_intersection'
    if abs(cv2.contourArea(vertices.astype(np.float32))) < 1e-6:
        return 'degenerate_area'
    return None


def raw_mask(vertices, shape=(256, 256)):
    mask = np.zeros(shape, np.uint8)
    if vertices is None or vertices.ndim != 2 or vertices.shape[1] != 2 or not len(vertices) or not np.isfinite(vertices).all():
        return mask
    height, width = shape
    contour = vertices.astype(np.float32)
    x0, x1 = max(0, math.floor(float(vertices[:, 0].min()))), min(width - 1, math.ceil(float(vertices[:, 0].max())))
    y0, y1 = max(0, math.floor(float(vertices[:, 1].min()))), min(height - 1, math.ceil(float(vertices[:, 1].max())))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            mask[y, x] = cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0
    return mask


def eligible_centres(mask):
    if mask.ndim != 2 or mask.dtype != np.uint8 or not np.isin(mask, [0, 1]).all():
        raise ValueError('Expected binary uint8 raw mask')
    kernel = np.zeros((5, 5), np.uint8)
    for x, y in SUPPORT:
        kernel[y + 2, x + 2] = 1
    return cv2.erode(mask, kernel, anchor=(2, 2), borderType=cv2.BORDER_CONSTANT, borderValue=0)


def neighbours(gray, ys, xs):
    """Float64 absolute coordinates; horizontal lerp then vertical lerp."""
    if gray.ndim != 2 or gray.dtype != np.float64 or not np.isfinite(gray).all():
        raise ValueError('Expected finite float64 grayscale')
    ys, xs = np.asarray(ys), np.asarray(xs)
    if ys.shape != xs.shape or ys.ndim != 1 or not np.issubdtype(ys.dtype, np.integer) or not np.issubdtype(xs.dtype, np.integer):
        raise ValueError('Expected matching integer centre arrays')
    result = []
    for dx, dy in OFFSETS:
        x, y = xs.astype(np.float64) + dx, ys.astype(np.float64) + dy
        x0, x1 = np.floor(x).astype(np.int64), np.ceil(x).astype(np.int64)
        y0, y1 = np.floor(y).astype(np.int64), np.ceil(y).astype(np.int64)
        if np.any(x0 < 0) or np.any(y0 < 0) or np.any(x1 >= gray.shape[1]) or np.any(y1 >= gray.shape[0]):
            raise ValueError('Out-of-image support; padding forbidden')
        tx, ty = x - x0, y - y0
        top = gray[y0, x0] + tx * (gray[y0, x1] - gray[y0, x0])
        bottom = gray[y1, x0] + tx * (gray[y1, x1] - gray[y1, x0])
        result.append(top + ty * (bottom - top))
    return np.stack(result, axis=1)


def raw_codes(gray, ys, xs):
    samples = neighbours(gray, ys, xs)
    bits = samples >= gray[ys, xs, None]
    return np.sum(bits.astype(np.uint16) * (1 << np.arange(8, dtype=np.uint16)), axis=1).astype(np.uint8)


def region_histogram(gray, mask, codebook):
    ys, xs = np.nonzero(eligible_centres(mask))
    if len(ys) < 64:
        raise ValueError('fewer_than_64_eligible_centres')
    codes = raw_codes(gray, ys, xs)
    counts = np.zeros(59, np.uint64)
    np.add.at(counts, codebook[codes], np.uint64(1))
    return counts, counts.astype(np.float64) / len(ys)


class Extractor:
    def __init__(self, context=None):
        self.context = Context() if context is None else context

    def extract(self, bgr, landmarks, image_id, source, gallery_lock=None):
        if gallery_lock is not None:
            self.context.require_lock(gallery_lock)
        try:
            polygons = self.context.polygons(landmarks)
        except ValueError as error:
            return self._missing(image_id, source, str(error))
        return self._extract_polygons(bgr, polygons, image_id, source)

    def _missing(self, image_id, source, reason, regions=None):
        return dict(image_id=image_id, source=source, **self.context.lock, status='missing_C1',
                    missing_reason=reason, regions={} if regions is None else regions,
                    counts=None, histograms=None, vector=None)

    def _extract_polygons(self, bgr, polygons, image_id, source):
        # Kept separate to test malformed/missing geometry before any image LBP.
        if bgr is None or bgr.shape != (256, 256, 3) or bgr.dtype != np.uint8:
            return self._missing(image_id, source, 'invalid_256x256_uint8_BGR_image')
        diagnostics, masks, failures = {}, {}, []
        for name in REGIONS:
            vertices = polygons.get(name)
            error = geometry_error(vertices)
            mask = raw_mask(vertices)
            centres = eligible_centres(mask)
            pixels, n = int(mask.sum()), int(centres.sum())
            if not error and not pixels:
                error = 'empty_mask'
            if not error and n < 64:
                error = 'fewer_than_64_eligible_centres'
            diagnostics[name] = dict(raw_mask_pixels=pixels, eligible_centres=n,
                                     raw_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
                                     geometry_status='invalid' if geometry_error(vertices) else 'valid',
                                     missing_reason=error)
            masks[name] = mask
            if error:
                failures.append(name + ':' + error)
        if failures:
            return self._missing(image_id, source, ';'.join(failures), diagnostics)
        gray = grayscale(bgr)
        values = [region_histogram(gray, masks[name], self.context.codebook) for name in REGIONS]
        counts, histograms = np.stack([v[0] for v in values]), np.stack([v[1] for v in values])
        vector = histograms.reshape(236).copy()
        validate_vector(vector)
        return dict(image_id=image_id, source=source, **self.context.lock, status='valid_C1', missing_reason=None,
                    regions=diagnostics, counts=counts, histograms=histograms, vector=vector)


def validate_vector(vector):
    if (vector.shape != (236,) or vector.dtype != np.float64 or not np.isfinite(vector).all()
            or np.any(vector < 0) or not np.allclose(vector.reshape(4, 59).sum(axis=1), 1., rtol=0., atol=1e-12)):
        raise ValueError('Invalid per-region L1 C1 float64 vector')


def chi_square(a, b):
    validate_vector(a)
    validate_vector(b)
    return float(0.5 * np.sum((a - b) ** 2 / (a + b + 1e-8)))
