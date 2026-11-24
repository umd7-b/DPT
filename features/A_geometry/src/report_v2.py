"""A150 v2: (raw - gallery_mean) / (raw_sigma + 1e-8), ddof=0.

Geometry extraction, mapping and A2 are reused unchanged. Normalized v2 vectors
and queries use float64; the immutable float32 raw matrix is only referenced.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from shared.report_v2 import (
    PROJECT_ROOT, digest, read_csv, save_csv, write_json, read_json, fresh_output,
    provenance, verify_sources, save_integrity, verify_integrity, finite_features, save_stats, load_stats)

LEGACY = PROJECT_ROOT / 'outputs/A_geometry/features'
DEFAULT_OUTPUT = PROJECT_ROOT / 'outputs/A_geometry/features_report_v2'
SCHEMA_ID = 'A150_report_v2.0.0'
EPSILON = 1e-8


def fit(raw):
    raw = finite_features(raw, 150, min_rows=2)
    mean, sigma = raw.mean(axis=0), raw.std(axis=0, ddof=0)
    return dict(schema_id=SCHEMA_ID, stage='a150', mean=mean, raw_sigma=sigma,
                epsilon=EPSILON, effective_divisor=sigma + EPSILON, ddof=0,
                fit_count=len(raw))


def validate_stats(stats):
    if str(stats.get('schema_id')) != SCHEMA_ID or str(stats.get('stage')) != 'a150':
        raise ValueError('Expected A150 report v2 statistics; legacy/B stats are forbidden')
    if float(stats['epsilon']) != EPSILON or int(stats['ddof']) != 0 or int(stats['fit_count']) < 2:
        raise ValueError('Invalid A v2 normalization configuration')
    for name in ('mean', 'raw_sigma', 'effective_divisor'):
        finite_features(stats[name], 150)
        if np.asarray(stats[name]).shape != (150,):
            raise ValueError('Invalid A v2 statistics shape')
    if np.any(stats['raw_sigma'] < 0) or not np.array_equal(stats['effective_divisor'], stats['raw_sigma'] + EPSILON):
        raise ValueError('A v2 divisor must equal raw_sigma + epsilon exactly')


def transform(raw, stats):
    validate_stats(stats)
    raw = finite_features(raw, 150)
    result = (raw - stats['mean']) / (stats['raw_sigma'] + float(stats['epsilon']))
    if not np.isfinite(result).all():
        raise ValueError('Non-finite A v2 normalized vector')
    return result


def build(output=DEFAULT_OUTPUT):
    started = time.perf_counter()
    sources = provenance([LEGACY / name for name in
        ('features_A_raw.npy', 'features_A_normalized.npy', 'geometry_stats.npz', 'metadata.csv')]
        + [PROJECT_ROOT / 'features/A_geometry/src/geometry_features.py', __file__])
    raw = np.load(LEGACY / 'features_A_raw.npy', allow_pickle=False)
    rows = read_csv(LEGACY / 'metadata.csv')
    if raw.shape != (len(rows), 150) or len(rows) != 1438:
        raise ValueError('A v2 expects the full unchanged 1438-image A150 gallery')
    records = [dict(row, image_id=row.get('image_id') or Path(row['image_name']).stem,
                    a_row_index=i) for i, row in enumerate(rows)]
    if len({r['image_id'] for r in records}) != len(records):
        raise ValueError('Duplicate A gallery identities')
    stats = fit(raw)
    normalized = transform(raw, stats)
    legacy_z = np.load(LEGACY / 'features_A_normalized.npy', allow_pickle=False).astype(np.float64)
    output = fresh_output(output, PROJECT_ROOT / 'outputs/A_geometry', 'features_report_v2')
    save_csv(output / 'metadata.csv', records)
    stats['fit_manifest_sha256'] = digest(output / 'metadata.csv')
    stats['raw_sha256'] = digest(LEGACY / 'features_A_raw.npy')
    save_stats(output / 'normalization_stats.npz', stats)
    np.save(output / 'features_A_normalized.npy', normalized, allow_pickle=False)
    write_json(output / 'raw_reference.json', dict(path=str(LEGACY / 'features_A_raw.npy'),
        sha256=stats['raw_sha256'], shape=list(raw.shape), dtype=str(raw.dtype), immutable=True))
    write_json(output / 'schema.json', dict(id=SCHEMA_ID, version='2.0.0', dimension=150,
        normalization='(raw-mean)/(raw_sigma+epsilon)', epsilon=EPSILON, ddof=0,
        normalized_dtype='float64', raw_dtype=str(raw.dtype), query_refit=False,
        authority='PDF section 2.5.2 + explicit user-approved v2 epsilon/ddof',
        geometry_status='Legacy mapping/eye centers/A2 unchanged; anatomical decisions remain UNVERIFIED'))
    write_json(output / 'source_provenance.json', sources)
    sigma_old = np.where(stats['raw_sigma'] < 1e-8, 1., stats['raw_sigma'])
    old_math = (raw.astype(np.float64) - stats['mean']) / sigma_old
    comparison = dict(raw_shape=list(raw.shape), normalized_shape=list(normalized.shape),
        legacy_dtype='float32', v2_dtype=str(normalized.dtype),
        changed_values_vs_saved_v1=int(np.count_nonzero(normalized != legacy_z)),
        max_absolute_difference_vs_saved_v1=float(np.max(np.abs(normalized - legacy_z))),
        max_formula_difference_before_legacy_float32_cast=float(np.max(np.abs(normalized - old_math))),
        legacy_float32_cast_max_error=float(np.max(np.abs(legacy_z - old_math))),
        zero_sigma_dimensions=np.flatnonzero(stats['raw_sigma'] == 0).tolist(),
        small_sigma_dimensions=np.flatnonzero(stats['raw_sigma'] < 1e-8).tolist(),
        epsilon=EPSILON, ddof=0, elapsed_seconds=time.perf_counter() - started)
    write_json(output / 'comparison_v1_v2.json', comparison)
    verify_sources(sources)
    save_integrity(output, ['schema.json', 'raw_reference.json', 'metadata.csv',
        'normalization_stats.npz', 'features_A_normalized.npy', 'source_provenance.json', 'comparison_v1_v2.json'])
    return comparison


def load_gallery(directory=DEFAULT_OUTPUT):
    directory = Path(directory).resolve()
    verify_integrity(directory)
    schema = read_json(directory / 'schema.json')
    if schema['id'] != SCHEMA_ID or schema['dimension'] != 150:
        raise ValueError('Expected A150 report v2 gallery')
    rows = read_csv(directory / 'metadata.csv')
    reference = read_json(directory / 'raw_reference.json')
    if digest(reference['path']) != reference['sha256']:
        raise ValueError('Immutable A raw reference changed')
    raw = np.load(reference['path'], allow_pickle=False)
    z = finite_features(np.load(directory / 'features_A_normalized.npy', allow_pickle=False), 150, min_rows=2)
    stats = load_stats(directory / 'normalization_stats.npz')
    validate_stats(stats)
    if raw.shape != z.shape or len(rows) != len(z) or int(stats['fit_count']) != len(rows):
        raise ValueError('A v2 gallery rows/statistics disagree')
    if str(stats['fit_manifest_sha256']) != digest(directory / 'metadata.csv') or str(stats['raw_sha256']) != reference['sha256']:
        raise ValueError('A v2 fit provenance mismatch')
    if not np.array_equal(z, transform(raw, stats)):
        raise ValueError('A v2 normalized vectors do not match their saved statistics')
    return rows, z, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    print(json.dumps(build(parser.parse_args().output), indent=2))


if __name__ == '__main__':
    main()
