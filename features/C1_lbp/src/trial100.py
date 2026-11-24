"""Run only the authenticated 100-image C1 technical trial (no database writes)."""
from pathlib import Path
from collections import Counter
from contextlib import closing
import csv
import hashlib
import json
import shutil
import sqlite3
import sys
import platform

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src.lbp236 import Context, Extractor, REGIONS, SPEC_DIR, sha256

OUT = ROOT / 'outputs/C1_lbp/trial100_spec_v0_1'
ARCHIVE = ROOT / 'docs/audits/evidence/dataset_landmarks478.npz'
ARCHIVE_HASH = 'a21e4abce28354d3a1fe5541bf0d2b7ab6d4b6d1119207d3231471bcacf263ed'
KNOWN_VIOLATIONS = {'hf_merged_00333': 'secondary_faces_visible',
                    'hf_merged_00561': 'secondary_face_visible',
                    'hf_merged_00722': 'hand_occludes_mouth'}


def write_json(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False,
                  default=lambda obj: obj.tolist() if isinstance(obj, np.ndarray) else obj.item())
        stream.write('\n')


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def inputs():
    if sha256(ARCHIVE) != ARCHIVE_HASH:
        raise ValueError('Saved478 archive authentication failed')
    with np.load(ARCHIVE, allow_pickle=False) as archive:
        names, points = archive['image_names'].tolist(), archive['points'].copy()
    if len(names) != 1438 or len(set(names)) != 1438 or points.shape != (1438, 478, 2) or points.dtype != np.float32:
        raise ValueError('Unexpected archive shape/dtype/identities')
    uri = (ROOT / 'database/data/portrait_ab_v2.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1'
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        images = {r['image_id']: dict(r) for r in connection.execute('SELECT * FROM Images')}
    # Explicit identity join; NPZ order is never assumed to match DB/catalog order.
    landmarks = {Path(name).stem: (i, points[i]) for i, name in enumerate(names)}
    return images, landmarks


def main():
    context = Context()
    output = OUT
    if (output / 'summary.json').exists() or (output / 'gallery_vectors.npy').exists() or (output / 'images').exists():
        raise FileExistsError('Trial already started/completed; refuse to overwrite')
    baseline = json.loads((output / 'evidence/baseline_before.json').read_text(encoding='utf-8'))
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or sha256(p) != h]
    if changed:
        raise ValueError('Protected artifacts changed: ' + repr(changed[:5]))
    plan_file = SPEC_DIR / 'trial100_manifest.json'
    if sha256(plan_file) != baseline[str(plan_file.resolve())]:
        raise ValueError('Frozen trial plan changed')
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    entries = plan['images']
    if (plan['schema_id'] != 'C1_TECHNICAL_TRIAL100_PLAN_v0.2.0' or len(entries) != 100
            or len({r['image_id'] for r in entries}) != 100 or Counter(r['source'] for r in entries) != {'cfd': 50, 'hf': 50}):
        raise ValueError('Not the exact balanced 100-image trial')
    images, landmarks = inputs()
    previous = {(r['image_id'], r['region']): r for r in read_csv(SPEC_DIR / 'metrics.csv')}
    (output / 'images').mkdir()
    shutil.copyfile(plan_file, output / 'input_trial100_manifest.json')
    write_json(output / 'contract_lock.json', dict(context.lock, roi_schema_id=context.roi['schema_id'],
               lbp_schema_id=context.spec['schema_id'], input_manifest_sha256=sha256(plan_file),
               landmark_archive_sha256=ARCHIVE_HASH, region_order=REGIONS, dtype='float64', dimension=236,
               normalization='four independent L1; no global normalization or fitted parameters',
               environment=dict(python=sys.version, numpy=np.__version__, opencv=cv2.__version__, platform=platform.platform())))
    extractor = Extractor(context)
    manifest, vectors, counts, histograms = [], [], [], []
    for entry in entries:
        identity = entry['image_id']
        image = images[identity]
        row_index, points = landmarks[identity]
        if image['source'] != entry['source'] or Path(image['filename']).stem != identity or sha256(image['image_path']) != image['image_hash']:
            raise ValueError('Image identity/provenance mismatch ' + identity)
        bgr = cv2.imread(image['image_path'], cv2.IMREAD_UNCHANGED)
        result = extractor.extract(bgr, points, identity, entry['source'])
        for region in REGIONS:
            measured, frozen = result['regions'][region], previous[(identity, region)]
            if (measured['raw_mask_pixels'] != int(frozen['raw_mask_pixels'])
                    or measured['eligible_centres'] != int(frozen['support_valid_centres'])
                    or measured['raw_mask_sha256'] != frozen['raw_mask_sha256']
                    or (measured['geometry_status'] == 'valid') != (frozen['geometry_valid'] == 'True')):
                raise ValueError('Geometry differs from frozen audit: ' + identity + '/' + region)
        feature_row = None
        if result['status'] == 'valid_C1':
            feature_row = len(vectors)
            vectors.append(result['vector']); counts.append(result['counts']); histograms.append(result['histograms'])
        result.update(feature_row_index=feature_row, filename=image['filename'], image_sha256=image['image_hash'],
                      landmark_archive_row_index=row_index, landmark_row_sha256=hashlib.sha256(points.tobytes()).hexdigest(),
                      included_for=entry['included_for'], anatomical_validation='UNVERIFIED',
                      dataset_criterion_violation=KNOWN_VIOLATIONS.get(identity),
                      dataset_status='KNOWN_VIOLATION' if identity in KNOWN_VIOLATIONS else 'NOT_CLEARED_BY_THIS_NUMERICAL_TRIAL')
        write_json(output / 'images' / (identity + '.json'), result)
        manifest.append({k: v for k, v in result.items() if k not in ('counts', 'histograms', 'vector', 'regions')})
        print(identity, result['status'], flush=True)
    for filename, array in [('gallery_vectors.npy', np.stack(vectors)), ('counts.npy', np.stack(counts)),
                            ('histograms.npy', np.stack(histograms))]:
        with (output / filename).open('xb') as stream:
            np.save(stream, array, allow_pickle=False)
    write_json(output / 'manifest.json', dict(context.lock, count=len(manifest), images=manifest))
    write_json(output / 'missing_C1.json', dict(context.lock, images=[r for r in manifest if r['status'] == 'missing_C1']))
    write_json(output / 'summary.json', dict(context.lock, input_count=len(manifest), valid_count=len(vectors),
               missing_count=len(manifest) - len(vectors), source_counts=dict(Counter(r['source'] for r in manifest)),
               known_dataset_violations={k: v for k, v in KNOWN_VIOLATIONS.items() if k in {r['image_id'] for r in manifest}},
               geometry_comparisons_to_frozen_audit=400, negative_images_have_no_counts_histograms_or_vector=True,
               database_writes=0, mediapipe_runs=0, c2_vectors_created=0, rankings_computed=0))
    print('Completed', len(manifest), 'images;', len(vectors), 'vectors; output', output, flush=True)


if __name__ == '__main__':
    main()
