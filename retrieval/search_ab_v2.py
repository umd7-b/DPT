"""Versioned A150/B144 retrieval using report v2 statistics and frozen v1 pairs.

Experimental two-set fusion only. Geometry/dataset decisions still unresolved by
the audit are retained, not silently promoted to full system compliance.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.A_geometry.src import report_v2 as a_v2
from features.B_color.src import report_v2 as b_v2
from retrieval import search_ab as legacy
from shared.report_v2 import (digest, read_csv, save_csv, write_json, read_json, pair_ids_digest)

OUT = ROOT / 'outputs/retrieval/ab_report_v2'
SOURCE_PAIRS = ROOT / 'outputs/retrieval/ab_experiment/calibration/representative_pairs.csv'
SCHEMA_ID = 'AB_report_v2.0.0'
VERSIONS = dict(a=a_v2.SCHEMA_ID, b=b_v2.SCHEMA_ID)
EPSILON = 1e-8
EXPERIMENT = 'A+B REPORT V2: experimental two-set 0.5/0.5 baseline, not official four-set fusion'


def load_gallery(a_directory=a_v2.DEFAULT_OUTPUT, b_directory=b_v2.DEFAULT_OUTPUT):
    a_directory, b_directory = Path(a_directory).resolve(), Path(b_directory).resolve()
    a_rows, av, _ = a_v2.load_gallery(a_directory)
    b_rows, bv, _, _ = b_v2.load_gallery(b_directory)
    gallery = legacy.join_galleries(a_rows, av, b_rows, bv)
    missing = {r['image_id']: r for r in read_csv(b_directory / 'missing_features.csv')}
    for row in gallery.missing_b:
        row['reason'] = missing.get(row['image_id'], {}).get('reason', 'No valid B descriptor')
    files = [a_directory / name for name in ('schema.json', 'metadata.csv', 'features_A_normalized.npy',
                                             'normalization_stats.npz', 'gallery_integrity.json')]
    files += [b_directory / name for name in ('schema.json', 'feature_rows.csv', 'features_B_normalized.npy',
        'moment_normalization_stats.npz', 'final_normalization_stats.npz', 'gallery_integrity.json')]
    gallery.fingerprint = {str(p): digest(p) for p in files}
    return gallery


def calibrate(gallery, directory=OUT / 'calibration', source_pairs=SOURCE_PAIRS):
    """Reuse exactly the old ordered pair IDs, NEVER the old distances/medians."""
    started = time.perf_counter()
    directory, source_pairs = Path(directory), Path(source_pairs).resolve()
    records = read_csv(source_pairs)
    pairs = [(r['image_id_1'], r['image_id_2']) for r in records]
    ids = [r['image_id'] for r in gallery.rows]
    positions = {key: i for i, key in enumerate(ids)}
    if not pairs or len(set(pairs)) != len(pairs) or any(i >= j or i not in positions or j not in positions for i, j in pairs):
        raise ValueError('Frozen pair IDs must be unique unordered non-self pairs in the v2 common gallery')
    contract = dict(schema_id=SCHEMA_ID, feature_versions=VERSIONS, fingerprint=gallery.fingerprint,
        source_pairs_file=str(source_pairs), source_pairs_sha256=digest(source_pairs),
        pair_ids_sha256=pair_ids_digest(pairs), pair_count=len(pairs), image_ids=ids, epsilon=EPSILON)
    params_path, pairs_path = directory / 'median_params.json', directory / 'representative_pairs.csv'
    if params_path.exists():
        params = read_json(params_path)
        if any(params.get(key) != value for key, value in contract.items()):
            raise ValueError('Wrong-version or stale v2 calibration; use a new v2 calibration directory')
        saved = read_csv(pairs_path)
        if digest(pairs_path) != params['pairs_sha256'] or [(r['image_id_1'], r['image_id_2']) for r in saved] != pairs:
            raise ValueError('V2 pair manifest integrity mismatch')
        for name in ('a', 'b'):
            value = params['median_' + name]
            expected = float(np.median([float(r['distance_' + name]) for r in saved]))
            if not math.isfinite(value) or value < 0 or value != expected:
                raise ValueError('V2 median disagrees with saved pair distances')
        return params, True
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError('V2 calibration directory must be new/empty')
    indices = np.array([(positions[i], positions[j]) for i, j in pairs], dtype=np.int64)
    da = legacy.pair_distances(gallery.a, indices)
    db = legacy.pair_distances(gallery.b, indices)
    directory.mkdir(parents=True, exist_ok=True)
    save_csv(pairs_path, [dict(image_id_1=i, image_id_2=j, distance_a=float(da[n]), distance_b=float(db[n]))
                         for n, (i, j) in enumerate(pairs)])
    params = dict(contract, median_a=float(np.median(da)), median_b=float(np.median(db)),
                  pairs_sha256=digest(pairs_path), formula='d/(median+epsilon)',
                  selection='Exact ordered pair identities retained from v1; distances recomputed on v2',
                  elapsed_seconds=time.perf_counter() - started)
    write_json(params_path, params)
    return params, False


def run_worker(kind, image, destination, gallery, python=None, skin_mask=None, hair_mask=None):
    environment = '.venv311' if kind == 'a' else '.venv-uniface'
    executable = Path(python).resolve() if python else ROOT / environment / 'Scripts/python.exe'
    if not executable.is_file():
        raise FileNotFoundError(f'Existing {environment} interpreter required: {executable}')
    command = [str(executable), '-X', 'utf8', '-B', '-m', 'retrieval.ab_query_worker_v2',
        '--kind', kind, '--image', str(image), '--output', str(destination), '--gallery', str(Path(gallery).resolve())]
    if skin_mask is not None:
        command += ['--skin-mask', str(skin_mask), '--hair-mask', str(hair_mask)]
    completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8')
    if completed.returncode:
        raise RuntimeError(f'V2 {kind.upper()} query worker failed:\n{completed.stdout}\n{completed.stderr}')
    status = read_json(destination / f'{kind}_status.json')
    if status['schema_id'] != VERSIONS[kind]:
        raise ValueError('Query worker returned statistics/vectors from a different version')
    return status


def query_vectors(image, gallery, destination, a_directory=a_v2.DEFAULT_OUTPUT,
                  b_directory=b_v2.DEFAULT_OUTPUT, python_a=None, python_b=None, skin_mask=None, hair_mask=None):
    ids, image_hash = legacy.identify_query(image, gallery)  # Retain documented byte-identity policy.
    if ids:
        common = [i for i, r in enumerate(gallery.rows) if r['image_id'] in ids]
        if common:
            i = common[0]
            return gallery.a[i], gallery.b[i], ids, dict(source='saved_normalized_v2', source_sha256=image_hash, feature_versions=VERSIONS)
        index = next(i for i, r in enumerate(gallery.a_rows) if legacy.image_id(r) in ids)
        reason = next((r['reason'] for r in gallery.missing_b if r['image_id'] in ids), 'No valid B')
        return gallery.all_a[index], None, ids, dict(source='saved_A_v2_missing_B', reason=reason,
            source_sha256=image_hash, feature_versions=VERSIONS)
    with tempfile.TemporaryDirectory(prefix='ab_report_v2_') as folder:
        temporary = Path(folder)
        a_status = run_worker('a', image, temporary, a_directory, python_a)
        b_status = run_worker('b', image, temporary, b_directory, python_b, skin_mask, hair_mask)
        if a_status['stats_sha256'] != digest(Path(a_directory) / 'normalization_stats.npz'):
            raise ValueError('Query A statistics fingerprint mismatch')
        if (b_status['moment_stats_sha256'] != digest(Path(b_directory) / 'moment_normalization_stats.npz')
                or b_status['final_stats_sha256'] != digest(Path(b_directory) / 'final_normalization_stats.npz')):
            raise ValueError('Query B stage statistics fingerprints mismatch')
        qa = np.load(temporary / 'query_A_normalized.npy', allow_pickle=False)
        qb = None if b_status['status'] != 'valid' else np.load(temporary / 'query_B_normalized.npy', allow_pickle=False)
        for path in temporary.glob('*.npy'):
            np.save(destination / path.name, np.load(path, allow_pickle=False), allow_pickle=False)
    if digest(image) != image_hash:
        raise ValueError('Query image changed while being extracted')
    return qa, qb, ids, dict(source='separate_environment_v2_workers', source_sha256=image_hash,
                            feature_versions=VERSIONS, a=a_status, b=b_status)


def preview(path, image, result, gallery, wa, wb):
    import cv2
    legacy.preview(path, image, result, gallery, wa, wb)
    canvas = cv2.imread(str(path))
    for row, mode in enumerate(result):
        y = row * 366
        canvas[y:y + 30] = 255
        cv2.putText(canvas, f'REPORT V2 | EXPERIMENTAL {mode} | A={wa:g} B={wb:g} | same A/B gallery',
                    (8, y + 20), 0, .5, (0, 0, 0), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(path), canvas):
        raise OSError('Cannot save v2 comparison preview')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--weight-a', type=float, default=.5)
    parser.add_argument('--weight-b', type=float, default=.5)
    parser.add_argument('--a-gallery', type=Path, default=a_v2.DEFAULT_OUTPUT)
    parser.add_argument('--b-gallery', type=Path, default=b_v2.DEFAULT_OUTPUT)
    parser.add_argument('--output', type=Path, help='New final query-output directory inside outputs/retrieval/ab_report_v2')
    parser.add_argument('--calibration-dir', type=Path, default=OUT / 'calibration')
    parser.add_argument('--python-a', type=Path)
    parser.add_argument('--python-b', type=Path)
    parser.add_argument('--skin-mask', type=Path)
    parser.add_argument('--hair-mask', type=Path)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        legacy.validate_weights(args.weight_a, args.weight_b)
        if args.top_k <= 0 or bool(args.skin_mask) != bool(args.hair_mask):
            raise ValueError('top-k must be positive; supply both raw masks together')
        for path in [args.calibration_dir] + ([args.output] if args.output else []):
            if OUT.resolve() not in path.resolve().parents:
                raise ValueError('V2 retrieval output must stay inside outputs/retrieval/ab_report_v2')
        gallery = load_gallery(args.a_gallery, args.b_gallery)
        image = legacy.resolve_image(args.image, gallery)
        output = args.output.resolve() if args.output else OUT / 'queries' / image.stem
        if output.exists():
            raise FileExistsError('Query output already exists; supply a new --output directory')
        params, reused = calibrate(gallery, args.calibration_dir)
        output.mkdir(parents=True)
        qa, qb, excluded, info = query_vectors(image, gallery, output, args.a_gallery, args.b_gallery,
                                              args.python_a, args.python_b, args.skin_mask, args.hair_mask)
        result = legacy.rankings(gallery, qa, qb, params, args.weight_a, args.weight_b, args.top_k, excluded)
        fields = ['rank', 'image_id', 'image_name', 'distance_a', 'distance_b', 'normalized_a', 'normalized_b', 'distance_total', 'score']
        for mode, rows in result.items():
            save_csv(output / f'{mode}_top{args.top_k}.csv', rows, fields)
        picture = output / f'comparison_top{args.top_k}.png'
        preview(picture, image, result, gallery, args.weight_a, args.weight_b)
        status = dict(schema_id=SCHEMA_ID, feature_versions=VERSIONS, experiment=EXPERIMENT,
            system_compliance='Normalization A12/B12 corrected; dataset/geometry UNVERIFIED or deviating items remain',
            status='valid' if qb is not None else 'missing_B', query=str(image), query_info=info,
            weights=dict(a=args.weight_a, b=args.weight_b), top_k=args.top_k, excluded_self_ids=sorted(excluded),
            gallery_a_count=len(gallery.a_rows), common_gallery_count=len(gallery.rows), missing_b=gallery.missing_b,
            missing_policy='Same valid A/B candidate intersection for all modes; missing-B query returns A-only, no zero-fill',
            fingerprint=gallery.fingerprint, calibration_file=str((args.calibration_dir / 'median_params.json').resolve()),
            calibration_reused=reused, pair_ids_sha256=params['pair_ids_sha256'], median_a=params['median_a'],
            median_b=params['median_b'], epsilon=params['epsilon'], results=result, preview=str(picture),
            elapsed_seconds=time.perf_counter() - started)
        write_json(output / 'results.json', status)
        print(EXPERIMENT)
        print(f"A={len(gallery.a_rows)}, common A/B={len(gallery.rows)}; query status={status['status']}")
        print(f"median A={params['median_a']:.12f}, B={params['median_b']:.12f}; v2 calibration reused={reused}")
        for mode, rows in result.items():
            print('\n' + mode.upper())
            for row in rows:
                db = 'N/A' if row['distance_b'] is None else f"{row['distance_b']:.9f}"
                total = 'N/A' if row['distance_total'] is None else f"{row['distance_total']:.9f}"
                print(f"{row['rank']}. {row['image_name']} | dA={row['distance_a']:.9f} | dB={db} | D={total}")
        print('\nPreview: ' + str(picture))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        parser.exit(2, f'Report v2 retrieval error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
