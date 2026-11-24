"""Experimental two-set A150 + B144 retrieval, following report section 2.5.

Only this module's output directory is writable. Existing pipelines and gallery
vectors are read-only. Heavy extractors run in their original Python environments.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import numpy as np

# Also support `python retrieval/search_ab.py` from any working directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

A_DIR = ROOT / 'outputs/A_geometry/features'
B_DIR = ROOT / 'outputs/B_color/color_features_full_v1'
OUT = ROOT / 'outputs/retrieval/ab_experiment'
REPORT_SHA256 = '8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80'
EXPERIMENT = 'Experimental A+B only; not official four-set A/B/C1/C2 fusion'
EPSILON = 1e-8  # Numerical convention: the PDF specifies epsilon, not its value.
SEED = 42
PAIR_COUNT = 20000


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False), encoding='utf-8')


def image_id(row):
    return row.get('image_id') or Path(row['image_name']).stem


def finite_matrix(matrix, count, dimension):
    value = np.asarray(matrix, dtype=np.float64)
    if value.shape != (count, dimension) or not np.isfinite(value).all():
        raise ValueError(f'Expected {count} finite vectors of dimension {dimension}')
    return value


def unique_rows(rows):
    result = {}
    names = set()
    for row in rows:
        identity = image_id(row)
        if identity in result or row['image_name'] in names:
            raise ValueError('Duplicate gallery identity: ' + identity)
        result[identity] = row
        names.add(row['image_name'])
    return result


@dataclass
class Gallery:
    rows: list
    a: np.ndarray
    b: np.ndarray
    a_rows: list
    all_a: np.ndarray
    missing_b: list
    fingerprint: dict


def join_galleries(a_rows, a, b_rows, b):
    """Resolve B via identity + explicit vector index; never zip A/B rows."""
    a = finite_matrix(a, len(a_rows), 150)
    b = finite_matrix(b, len(b_rows), 144)
    a_index = unique_rows(a_rows)
    unique_rows(b_rows)
    a_positions = {image_id(row): i for i, row in enumerate(a_rows)}
    b_positions = set()
    matches = {}
    for row in b_rows:
        identity = image_id(row)
        if identity not in a_index:
            raise ValueError('B identity absent from A: ' + identity)
        ai = a_positions[identity]
        if row['image_name'] != a_index[identity]['image_name']:
            raise ValueError('A/B filename mismatch: ' + identity)
        if row.get('a_row_index') not in (None, '') and int(row['a_row_index']) != ai:
            raise ValueError('A/B a_row_index mismatch: ' + identity)
        bi = int(row['feature_row_index'])
        if bi < 0 or bi >= len(b) or bi in b_positions:
            raise ValueError('Invalid/duplicate B feature_row_index')
        if row.get('status', 'valid') != 'valid':
            raise ValueError('Non-valid row in B feature_rows')
        b_positions.add(bi)
        matches[identity] = (ai, bi, row)
    ids = sorted(matches)
    rows = [dict(matches[key][2], image_id=key,
                 a_row_index=matches[key][0]) for key in ids]
    missing = [dict(row, image_id=image_id(row), a_row_index=i)
               for i, row in enumerate(a_rows) if image_id(row) not in matches]
    return Gallery(rows, a[[matches[key][0] for key in ids]],
                   b[[matches[key][1] for key in ids]], a_rows, a, missing, {})


def load_gallery(a_dir=A_DIR, b_dir=B_DIR):
    a_dir, b_dir = Path(a_dir), Path(b_dir)
    # Validate the existing approved B artifact without importing an extractor.
    integrity = json.loads((b_dir / 'gallery_integrity.json').read_text(encoding='utf-8'))
    for name, expected in integrity.items():
        path = (b_dir / name).resolve()
        if b_dir.resolve() not in path.parents or digest(path) != expected:
            raise ValueError('B gallery integrity mismatch: ' + name)
    schema = json.loads((b_dir / 'schema.json').read_text(encoding='utf-8'))
    if schema['id'] != 'B144_raw_v1.0.0':
        raise ValueError('Expected approved B144_raw_v1.0.0 gallery')
    a_rows = read_csv(a_dir / 'metadata.csv')
    b_rows = read_csv(b_dir / 'feature_rows.csv')
    result = join_galleries(a_rows, np.load(a_dir / 'features_A_normalized.npy', allow_pickle=False),
                            b_rows, np.load(b_dir / 'features_B_normalized.npy', allow_pickle=False))
    missing_status = {image_id(row): row for row in read_csv(b_dir / 'missing_features.csv')}
    for row in result.missing_b:
        row['reason'] = missing_status.get(row['image_id'], {}).get('reason', 'No valid B vector')
    sources = [a_dir / name for name in ('metadata.csv', 'features_A_normalized.npy', 'geometry_stats.npz')]
    sources += [b_dir / name for name in ('feature_rows.csv', 'features_B_normalized.npy',
                                        'normalization_stats.npz', 'gallery_integrity.json', 'missing_features.csv')]
    result.fingerprint = {str(path.resolve()): digest(path) for path in sources}
    return result


def representative_pairs(count, seed=SEED, pair_count=PAIR_COUNT):
    """Uniform sample without replacement from unordered non-self pairs.

    Gallery identities must be sorted before calling. The exact selected image
    identities are persisted so reuse does not depend on a future RNG version.
    """
    if count < 2 or pair_count <= 0:
        raise ValueError('Median calibration needs >=2 images and positive pair count')
    left, right = np.triu_indices(count, k=1)
    selected = sorted(random.Random(seed).sample(range(len(left)), min(pair_count, len(left))))
    return np.column_stack((left[selected], right[selected]))


def pair_distances(matrix, pairs):
    # Bounded temporary allocation even if the requested sample is enlarged.
    distances = np.empty(len(pairs), dtype=np.float64)
    for start in range(0, len(pairs), 2048):
        block = pairs[start:start + 2048]
        distances[start:start + len(block)] = np.linalg.norm(matrix[block[:, 0]] - matrix[block[:, 1]], axis=1)
    return distances


def calibrate(gallery, directory, seed=SEED, pair_count=PAIR_COUNT):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'median_params.json'
    pair_path = directory / 'representative_pairs.csv'
    contract = dict(version=1, fingerprint=gallery.fingerprint, seed=seed,
                    requested_pair_count=pair_count, epsilon=EPSILON,
                    image_ids=[row['image_id'] for row in gallery.rows])
    if path.exists():
        params = json.loads(path.read_text(encoding='utf-8'))
        if any(params.get(key) != value for key, value in contract.items()):
            raise ValueError('Stale median calibration; use a new --calibration-dir for changed galleries/settings')
        if not pair_path.is_file() or digest(pair_path) != params['pairs_sha256']:
            raise ValueError('Median pair manifest is missing or changed')
        for key in ('median_a', 'median_b'):
            if not math.isfinite(params[key]) or params[key] < 0:
                raise ValueError('Invalid saved median')
        saved_pairs = read_csv(pair_path)
        if len(saved_pairs) != params['pair_count'] or any(
                float(np.median([float(row['distance_' + key]) for row in saved_pairs])) != params['median_' + key]
                for key in ('a', 'b')):
            raise ValueError('Saved median disagrees with pair distances')
        return params, True
    pairs = representative_pairs(len(gallery.rows), seed, pair_count)
    da, db = pair_distances(gallery.a, pairs), pair_distances(gallery.b, pairs)
    records = [dict(image_id_1=gallery.rows[i]['image_id'], image_id_2=gallery.rows[j]['image_id'],
                    distance_a=float(da[n]), distance_b=float(db[n])) for n, (i, j) in enumerate(pairs)]
    write_csv(pair_path, records, ['image_id_1', 'image_id_2', 'distance_a', 'distance_b'])
    source_pairs = {}
    for i, j in pairs:
        key = '/'.join(sorted([gallery.rows[i].get('dataset_source', 'unknown'),
                               gallery.rows[j].get('dataset_source', 'unknown')]))
        source_pairs[key] = source_pairs.get(key, 0) + 1
    params = dict(contract, median_a=float(np.median(da)), median_b=float(np.median(db)),
                  pair_count=len(pairs), pairs_sha256=digest(pair_path), source_pair_counts=source_pairs,
                  selection='Uniform unordered non-self pairs without replacement from sorted A/B intersection; random.Random(seed)',
                  report_sha256=REPORT_SHA256, report_section='2.5.2, PDF page 17',
                  epsilon_convention='1e-8 is an implementation choice; PDF does not fix its value')
    write_json(path, params)
    return params, False


def validate_weights(weight_a, weight_b):
    if (not all(math.isfinite(w) and w >= 0 for w in (weight_a, weight_b))
            or not math.isclose(weight_a + weight_b, 1., rel_tol=0., abs_tol=1e-12)):
        raise ValueError('Weights must be finite, nonnegative and sum to 1')


def rankings(gallery, query_a, query_b, params, weight_a=.5, weight_b=.5,
             top_k=5, exclude_ids=()):
    validate_weights(weight_a, weight_b)
    if top_k <= 0:
        raise ValueError('top-k must be positive')
    query_a = finite_matrix(np.asarray(query_a).reshape(1, -1), 1, 150)[0]
    if query_b is not None:
        query_b = finite_matrix(np.asarray(query_b).reshape(1, -1), 1, 144)[0]
    da = np.linalg.norm(gallery.a - query_a, axis=1)
    db = None if query_b is None else np.linalg.norm(gallery.b - query_b, axis=1)
    na = da / (params['median_a'] + params['epsilon'])
    nb = None if db is None else db / (params['median_b'] + params['epsilon'])
    total = None if db is None else weight_a * na + weight_b * nb
    excluded = set(exclude_ids)
    names = np.array([row['image_name'] for row in gallery.rows])
    result = {}
    for mode, scores in (('ab', total), ('a_only', na), ('b_only', nb)):
        rows = []
        if scores is not None:
            indices = [i for i in np.lexsort((names, scores)) if gallery.rows[i]['image_id'] not in excluded][:top_k]
            for rank, i in enumerate(indices, 1):
                rows.append(dict(rank=rank, image_id=gallery.rows[i]['image_id'], image_name=names[i],
                                 distance_a=float(da[i]), distance_b=None if db is None else float(db[i]),
                                 normalized_a=float(na[i]), normalized_b=None if nb is None else float(nb[i]),
                                 distance_total=None if total is None else float(total[i]),
                                 score=float(scores[i])))
        result[mode] = rows
    return result


def resolve_image(value, gallery):
    path = Path(value)
    if path.is_file():
        return path.resolve()
    if path.name == str(path):
        candidates = {Path(row['image_path']).resolve() for row in gallery.a_rows if row['image_name'] == path.name}
        if len(candidates) == 1 and next(iter(candidates)).is_file():
            return next(iter(candidates))
    raise FileNotFoundError(f'Query image not found: {value}')


def identify_query(path, gallery):
    """Content identity avoids using a saved vector for an unrelated same-name file."""
    query_hash = digest(path)
    ids = {row['image_id'] for row in gallery.rows if row['source_sha256'] == query_hash}
    # B-missing images still have A identity; detect renamed copies as well.
    for row in gallery.a_rows:
        if image_id(row) in ids:
            continue
        if digest(Path(row['image_path'])) == query_hash:
            ids.add(image_id(row))
    return ids, query_hash


def run_worker(kind, image, destination, python=None, skin_mask=None, hair_mask=None):
    environment = '.venv311' if kind == 'a' else '.venv-uniface'
    executable = Path(python) if python else ROOT / environment / 'Scripts/python.exe'
    if not executable.is_file():
        raise FileNotFoundError(f'Existing {environment} Python required: {executable}')
    command = [str(executable), '-X', 'utf8', '-B', '-m', 'retrieval.ab_query_worker',
               '--kind', kind, '--image', str(image), '--output', str(destination)]
    if skin_mask is not None:
        command += ['--skin-mask', str(skin_mask), '--hair-mask', str(hair_mask)]
    completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8')
    if completed.returncode:
        raise RuntimeError(f'{kind.upper()} extraction failed in {environment}:\n{completed.stdout}\n{completed.stderr}')
    return json.loads((destination / f'{kind}_status.json').read_text(encoding='utf-8'))


def query_vectors(path, gallery, destination, python_a=None, python_b=None,
                  skin_mask=None, hair_mask=None):
    ids, source_hash = identify_query(path, gallery)
    if ids:
        common = [i for i, row in enumerate(gallery.rows) if row['image_id'] in ids]
        if common:
            i = common[0]
            return gallery.a[i], gallery.b[i], ids, dict(source='saved_normalized_vectors', source_sha256=source_hash)
        ai = next(i for i, row in enumerate(gallery.a_rows) if image_id(row) in ids)
        reason = next((row['reason'] for row in gallery.missing_b if row['image_id'] in ids), 'No valid B vector')
        return gallery.all_a[ai], None, ids, dict(source='saved_A_only', source_sha256=source_hash, reason=reason)
    # Intermediate vectors are private and never written into A/B artifact folders.
    with tempfile.TemporaryDirectory(prefix='ab_query_') as temporary:
        temporary = Path(temporary)
        a_status = run_worker('a', path, temporary, python_a)
        b_status = run_worker('b', path, temporary, python_b, skin_mask, hair_mask)
        qa = np.load(temporary / 'query_A_normalized.npy', allow_pickle=False)
        qb = None if b_status['status'] != 'valid' else np.load(temporary / 'query_B_normalized.npy', allow_pickle=False)
        for name in ('query_A_normalized.npy', 'query_B_normalized.npy'):
            if (temporary / name).exists():
                np.save(destination / name, np.load(temporary / name, allow_pickle=False), allow_pickle=False)
    if digest(path) != source_hash:
        raise ValueError('Query image changed during extraction')
    return qa, qb, ids, dict(source='separate_environment_workers', source_sha256=source_hash,
                            a=a_status, b=b_status)


def preview(path, query_path, results, gallery, weight_a, weight_b):
    import cv2
    tile_w, tile_h = 256, 366
    columns = 1 + max(1, *(len(rows) for rows in results.values()))
    canvas = np.full((tile_h * 3, tile_w * columns, 3), 255, np.uint8)
    lookup = {row['image_id']: row for row in gallery.rows}
    for y, (mode, rows) in enumerate(results.items()):
        offset = y * tile_h
        method = (f'A+B | A={weight_a:g} B={weight_b:g}' if mode == 'ab'
                  else ('A-only | rank by normalized dA' if mode == 'a_only'
                        else 'B-only | rank by normalized dB'))
        title = f'EXPERIMENTAL {method} | same A/B gallery'
        cv2.putText(canvas, title, (8, offset + 20), 0, .55, (0, 0, 0), 1, cv2.LINE_AA)
        for col, row in enumerate([None] + rows):
            source = query_path if row is None else Path(lookup[row['image_id']]['image_path'])
            image = cv2.imread(str(source))
            if image is None:
                raise ValueError('Cannot read preview image: ' + str(source))
            x = col * tile_w
            canvas[offset + 30:offset + 286, x:x + tile_w] = cv2.resize(image, (256, 256))
            labels = [query_path.name, 'QUERY'] if row is None else [
                f"#{row['rank']} {row['image_name']}",
                f"dA={row['distance_a']:.5f} dB=" + ('N/A' if row['distance_b'] is None else f"{row['distance_b']:.5f}"),
                'AB=' + ('N/A' if row['distance_total'] is None else f"{row['distance_total']:.6f}") + f" score={row['score']:.6f}"]
            for line, label in enumerate(labels):
                cv2.putText(canvas, label, (x + 5, offset + 307 + 22 * line), 0, .41, (0, 0, 0), 1, cv2.LINE_AA)
        if not rows:
            cv2.putText(canvas, 'Unavailable: query has no valid B; no zero-fill', (tile_w + 8, offset + 100), 0, .6, (0, 0, 150), 1)
    if not cv2.imwrite(str(path), canvas):
        raise OSError('Cannot save preview: ' + str(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Existing gallery filename or a new aligned 256x256 image path')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--weight-a', type=float, default=.5)
    parser.add_argument('--weight-b', type=float, default=.5)
    parser.add_argument('--output', type=Path, default=OUT / 'queries')
    parser.add_argument('--calibration-dir', type=Path, default=OUT / 'calibration')
    parser.add_argument('--python-a', type=Path, help='Existing Python with MediaPipe; defaults to .venv311')
    parser.add_argument('--python-b', type=Path, help='Existing Python with UniFace; defaults to .venv-uniface')
    parser.add_argument('--skin-mask', type=Path, help='Optional raw class-1 mask for a new query')
    parser.add_argument('--hair-mask', type=Path, help='Optional raw class-17 mask for a new query')
    args = parser.parse_args(argv)
    try:
        validate_weights(args.weight_a, args.weight_b)
        if args.top_k <= 0:
            raise ValueError('top-k must be positive')
        if bool(args.skin_mask) != bool(args.hair_mask):
            raise ValueError('Supply both --skin-mask and --hair-mask')
        # Enforce that CLI output options cannot overwrite the existing pipelines.
        output_root = (ROOT / 'outputs/retrieval').resolve()
        for path in (args.output, args.calibration_dir):
            if output_root not in path.resolve().parents:
                raise ValueError('Outputs must be dedicated subdirectories of outputs/retrieval')
        gallery = load_gallery()
        image = resolve_image(args.image, gallery)
        params, reused = calibrate(gallery, args.calibration_dir)
        output = args.output.resolve() / image.stem
        output.mkdir(parents=True, exist_ok=True)
        qa, qb, exclude_ids, query_status = query_vectors(image, gallery, output, args.python_a, args.python_b,
                                                         args.skin_mask, args.hair_mask)
        result = rankings(gallery, qa, qb, params, args.weight_a, args.weight_b, args.top_k, exclude_ids)
        fields = ['rank', 'image_id', 'image_name', 'distance_a', 'distance_b', 'normalized_a',
                  'normalized_b', 'distance_total', 'score']
        for mode, rows in result.items():
            write_csv(output / f'{mode}_top{args.top_k}.csv', rows, fields)
        preview_path = output / f'comparison_top{args.top_k}.png'
        preview(preview_path, image, result, gallery, args.weight_a, args.weight_b)
        status = dict(experiment=EXPERIMENT, status='valid' if qb is not None else 'missing_B',
                      formula='D = weight_a*dA/(median_a+epsilon) + weight_b*dB/(median_b+epsilon)',
                      weights=dict(a=args.weight_a, b=args.weight_b), query=str(image), query_info=query_status,
                      excluded_self_ids=sorted(exclude_ids), top_k=args.top_k, gallery_a_count=len(gallery.a_rows),
                      common_gallery_count=len(gallery.rows), missing_b=gallery.missing_b,
                      missing_policy='Exclude B-missing candidates for all three modes; query missing B returns A-only and empty AB/B-only',
                      calibration_file=str(args.calibration_dir.resolve() / 'median_params.json'),
                      calibration_reused=reused, median_a=params['median_a'], median_b=params['median_b'],
                      epsilon=params['epsilon'], fingerprint=gallery.fingerprint, results=result, preview=str(preview_path))
        write_json(output / 'results.json', status)
        print(EXPERIMENT)
        print(f"Gallery: A={len(gallery.a_rows)}, common A/B={len(gallery.rows)}; missing B={len(gallery.missing_b)}")
        print(f"Medians: A={params['median_a']:.9f}, B={params['median_b']:.9f}; reused={reused}")
        print(f"Query status: {status['status']}")
        if qb is None:
            print('AB and B-only unavailable: ' + query_status.get('reason', str(query_status.get('b'))))
        for mode, rows in result.items():
            print(f'\n{mode.upper()} TOP-{args.top_k}')
            for row in rows:
                db = 'N/A' if row['distance_b'] is None else f"{row['distance_b']:.6f}"
                total = 'N/A' if row['distance_total'] is None else f"{row['distance_total']:.6f}"
                print(f"{row['rank']}. {row['image_name']} | dA={row['distance_a']:.6f} | dB={db} | D_AB={total} | score={row['score']:.6f}")
        print('\nPreview: ' + str(preview_path))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        parser.exit(2, f'AB search error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
