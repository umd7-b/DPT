"""B144 v2: normalize Lab24 in separate regions BEFORE concatenating B144.

The final all144 Z-score is a second, independently fitted stage. Both stages
use the approved B rule sigma<1e-8 -> divisor1, never A's sigma+epsilon.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from features.B_color.src.color_features import region_descriptor, validate_image, validate_mask
from shared.report_v2 import (
    PROJECT_ROOT, digest, read_csv, save_csv, write_json, read_json, fresh_output,
    provenance, verify_sources, save_integrity, verify_integrity, finite_features, save_stats, load_stats)
from shared.paths import DATASET_ROOT

LEGACY = PROJECT_ROOT / 'outputs/B_color/color_features_full_v1'
UNIFACE = PROJECT_ROOT / 'outputs/B_color/uniface_full'
DEFAULT_OUTPUT = PROJECT_ROOT / 'outputs/B_color/color_features_report_v2'
SCHEMA_ID = 'B144_report_v2.0.0'
THRESHOLD = 1e-8
MOMENT_INDICES = np.r_[48:60, 120:132]


def describe_regions(image, skin_mask, hair_mask):
    """Reuse the unchanged raw descriptor in each region; do not concatenate yet."""
    validate_image(image)
    validate_mask(skin_mask, image.shape[:2])
    validate_mask(hair_mask, image.shape[:2])
    if np.any((skin_mask > 0) & (hair_mask > 0)):
        raise ValueError('Skin/hair masks overlap')
    skin, skin_info = region_descriptor(image, skin_mask, min_pixels=100)
    hair, hair_info = region_descriptor(image, hair_mask, min_pixels=100)
    status = dict(status='valid' if skin is not None and hair is not None else 'missing_B',
                  skin=skin_info, hair=hair_info)
    return skin, hair, status


def fit_stage(matrix, stage):
    if stage not in ('moments24', 'final144'):
        raise ValueError('B v2 only supports moments24 followed by final144')
    dimension = 24 if stage == 'moments24' else 144
    matrix = finite_features(matrix, dimension, min_rows=2)
    sigma = matrix.std(axis=0, ddof=0)
    return dict(schema_id=SCHEMA_ID, stage=stage, dimension=dimension,
                mean=matrix.mean(axis=0), raw_sigma=sigma,
                effective_divisor=np.where(sigma < THRESHOLD, 1., sigma),
                std_threshold=THRESHOLD, small_std_divisor=1., ddof=0, fit_count=len(matrix))


def validate_stats(stats, stage):
    dimension = 24 if stage == 'moments24' else 144
    if (stage not in ('moments24', 'final144') or str(stats.get('schema_id')) != SCHEMA_ID
            or str(stats.get('stage')) != stage or int(stats.get('dimension', -1)) != dimension):
        raise ValueError('Expected matching B report v2 stage statistics; v1/A/wrong-stage stats forbidden')
    if (int(stats['ddof']) != 0 or float(stats['std_threshold']) != THRESHOLD
            or float(stats['small_std_divisor']) != 1. or int(stats['fit_count']) < 2):
        raise ValueError('Invalid B v2 normalization conventions')
    for name in ('mean', 'raw_sigma', 'effective_divisor'):
        finite_features(stats[name], dimension)
        if np.asarray(stats[name]).shape != (dimension,):
            raise ValueError('Invalid B v2 statistics shape')
    expected = np.where(stats['raw_sigma'] < THRESHOLD, 1., stats['raw_sigma'])
    if np.any(stats['raw_sigma'] < 0) or not np.array_equal(expected, stats['effective_divisor']):
        raise ValueError('B v2 must use the approved threshold divisor, not sigma+epsilon')


def apply_stage(matrix, stats, stage):
    validate_stats(stats, stage)
    dimension = 24 if stage == 'moments24' else 144
    matrix = finite_features(matrix, dimension)
    result = (matrix - stats['mean']) / stats['effective_divisor']
    if not np.isfinite(result).all():
        raise ValueError('Non-finite B v2 normalized vector')
    return result


def normalize_moments_before_concat(skin72, hair72, moment_stats):
    """Keep two regions separate while changing ONLY their 12 Lab moments each."""
    skin = finite_features(skin72, 72).copy()
    hair = finite_features(hair72, 72).copy()
    if skin.shape != hair.shape:
        raise ValueError('Skin/hair region shapes must agree')
    moments24 = np.concatenate((skin[..., 48:60], hair[..., 48:60]), axis=-1)
    moments_z = apply_stage(moments24, moment_stats, 'moments24')
    skin[..., 48:60] = moments_z[..., :12]
    hair[..., 48:60] = moments_z[..., 12:]
    return skin, hair


def assemble_after_moments(skin72, hair72, moment_stats):
    skin, hair = normalize_moments_before_concat(skin72, hair72, moment_stats)
    return np.concatenate((skin, hair), axis=-1)  # B144 concatenation happens AFTER the Lab stage.


def fit_pipeline(skin72, hair72):
    skin = finite_features(skin72, 72, min_rows=2)
    hair = finite_features(hair72, 72, min_rows=2)
    if skin.shape != hair.shape:
        raise ValueError('Skin/hair gallery shapes must agree')
    moments = np.concatenate((skin[:, 48:60], hair[:, 48:60]), axis=1)
    moment_stats = fit_stage(moments, 'moments24')
    after_moments = assemble_after_moments(skin, hair, moment_stats)
    final_stats = fit_stage(after_moments, 'final144')
    return after_moments, apply_stage(after_moments, final_stats, 'final144'), moment_stats, final_stats


def transform_regions(skin72, hair72, moment_stats, final_stats):
    after_moments = assemble_after_moments(skin72, hair72, moment_stats)
    return apply_stage(after_moments, final_stats, 'final144')


def build(output=DEFAULT_OUTPUT):
    # Existing input checker is read-only; no batch writer/segmentation is called.
    from features.B_color.src.full_color import verified_input, descriptor_checks
    from features.B_color.src.search_full_color import load_gallery as load_legacy
    started = time.perf_counter()
    old_rows, old_raw, old_z, _ = load_legacy(LEGACY)
    old_index = {r['image_id']: int(r['feature_row_index']) for r in old_rows}
    manifest = read_csv(LEGACY / 'manifest.csv')
    a_rows = read_csv(PROJECT_ROOT / 'outputs/A_geometry/features/metadata.csv')
    metrics = {r['image_name']: r for r in read_csv(UNIFACE / 'metrics.csv')}
    if len(manifest) != 1438 or [r['image_name'] for r in manifest] != [r['image_name'] for r in a_rows]:
        raise ValueError('B input manifest must retain all 1438 A identities/order')
    source_paths = [LEGACY / name for name in ('features_B_raw.npy', 'features_B_normalized.npy',
        'normalization_stats.npz', 'manifest.csv', 'feature_rows.csv', 'gallery_integrity.json')]
    source_paths += [PROJECT_ROOT / 'features/B_color/src/color_features.py', __file__, UNIFACE / 'metrics.csv']
    for row in manifest:
        source_paths += [Path(row[key]) for key in ('image_path', 'skin_mask_path', 'hair_mask_path')]
        source_paths.append(UNIFACE / 'receipts' / f"{row['image_id']}.json")
    sources = provenance(source_paths)
    skins, hairs, valid_rows, all_rows = [], [], [], []
    for i, original in enumerate(manifest):
        image, skin_mask, hair_mask, _ = verified_input(DATASET_ROOT, UNIFACE, original, metrics[original['image_name']])
        skin, hair, status = describe_regions(image, skin_mask, hair_mask)
        row = dict(original, vector_schema_id=SCHEMA_ID)
        if status['status'] == 'valid':
            if original['image_id'] not in old_index:
                raise ValueError('B validity changed relative to the protected baseline')
            # Raw serialization for comparison/storage does not enter v2 normalization.
            raw_reference = np.concatenate((skin, hair))
            if not np.array_equal(raw_reference, old_raw[old_index[original['image_id']]]):
                raise ValueError('Recomputed raw B descriptor differs from immutable baseline: ' + original['image_id'])
            row['feature_row_index'] = len(skins)
            skins.append(skin); hairs.append(hair); valid_rows.append(row)
        elif original['status'] == 'valid':
            raise ValueError('A previously valid B descriptor became missing')
        all_rows.append(row)
        if (i + 1) % 300 == 0:
            print(f'B v2 raw regions verified {i + 1}/1438', flush=True)
    if len(valid_rows) != len(old_rows):
        raise ValueError('B v2 valid identity set differs from baseline')
    skin_matrix, hair_matrix = np.asarray(skins), np.asarray(hairs)
    after, normalized, moment_stats, final_stats = fit_pipeline(skin_matrix, hair_matrix)
    raw = np.concatenate((skin_matrix, hair_matrix), axis=1)
    descriptor_checks(raw)
    output = fresh_output(output, PROJECT_ROOT / 'outputs/B_color', 'color_features_report_v2')
    save_csv(output / 'manifest.csv', all_rows)
    save_csv(output / 'feature_rows.csv', valid_rows)
    save_csv(output / 'fit_manifest.csv', [dict(image_id=r['image_id'], a_row_index=r['a_row_index'],
        feature_row_index=r['feature_row_index'], source_sha256=r['source_sha256']) for r in valid_rows])
    save_csv(output / 'missing_features.csv', [r for r in all_rows if r['status'] != 'valid'], list(all_rows[0]))
    fit_hash = digest(output / 'fit_manifest.csv')
    for stats in (moment_stats, final_stats):
        stats['fit_manifest_sha256'] = fit_hash
    save_stats(output / 'moment_normalization_stats.npz', moment_stats)
    save_stats(output / 'final_normalization_stats.npz', final_stats)
    np.save(output / 'features_B_raw.npy', raw, allow_pickle=False)
    np.save(output / 'features_B_after_moments.npy', after, allow_pickle=False)
    np.save(output / 'features_B_normalized.npy', normalized, allow_pickle=False)
    write_json(output / 'schema.json', dict(id=SCHEMA_ID, version='2.0.0', dimension=144,
        regions=['skin72', 'hair72'], moment_indices=MOMENT_INDICES.tolist(),
        normalization_stages=['Lab24 Z-score on separate regions', 'concatenate Skin72+Hair72', 'all144 Z-score'],
        moment_stage='ddof0; sigma<1e-8 -> divisor1', final_stage='D15: ddof0; sigma<1e-8 -> divisor1',
        raw_skin_class=1, raw_hair_class=17, erosion=False, include_nose=False, minimum_pixels=100,
        descriptor='Unchanged approved HS48/Lab12/Hue12; Pearson kurtosis; approved circular statistics',
        missing_policy='No B144 when either region is missing; no zero-fill', normalized_dtype='float64',
        query_refit=False, authority='PDF sections 2.3.3/2.5.2 + explicit v2 two-stage user decision'))
    write_json(output / 'source_provenance.json', sources)
    comparison = dict(input_images=len(all_rows), valid_vectors=len(valid_rows),
        missing_images=[r['image_id'] for r in all_rows if r['status'] != 'valid'],
        shape=list(raw.shape), raw_recomputed_exactly_equal_to_v1=bool(np.array_equal(raw, old_raw)),
        moment_stats_shape=list(moment_stats['mean'].shape), final_stats_shape=list(final_stats['mean'].shape),
        max_normalized_difference_vs_v1=float(np.max(np.abs(normalized - old_z))),
        changed_normalized_values=int(np.count_nonzero(normalized != old_z)),
        moment_raw_small_sigma=np.flatnonzero(moment_stats['raw_sigma'] < THRESHOLD).tolist(),
        final_small_sigma=np.flatnonzero(final_stats['raw_sigma'] < THRESHOLD).tolist(),
        after_moment_lab_max_abs_mean=float(np.max(np.abs(after[:, MOMENT_INDICES].mean(axis=0)))),
        after_moment_lab_max_std_error=float(np.max(np.abs(after[:, MOMENT_INDICES].std(axis=0) - 1))),
        elapsed_seconds=time.perf_counter() - started)
    write_json(output / 'comparison_v1_v2.json', comparison)
    verify_sources(sources)
    save_integrity(output, ['schema.json', 'manifest.csv', 'feature_rows.csv', 'fit_manifest.csv',
        'missing_features.csv', 'moment_normalization_stats.npz', 'final_normalization_stats.npz',
        'features_B_raw.npy', 'features_B_after_moments.npy', 'features_B_normalized.npy',
        'source_provenance.json', 'comparison_v1_v2.json'])
    return comparison


def load_gallery(directory=DEFAULT_OUTPUT):
    directory = Path(directory).resolve()
    verify_integrity(directory)
    if read_json(directory / 'schema.json')['id'] != SCHEMA_ID:
        raise ValueError('Expected B144 report v2 gallery')
    rows = read_csv(directory / 'feature_rows.csv')
    raw = finite_features(np.load(directory / 'features_B_raw.npy', allow_pickle=False), 144, min_rows=2)
    after = finite_features(np.load(directory / 'features_B_after_moments.npy', allow_pickle=False), 144, min_rows=2)
    z = finite_features(np.load(directory / 'features_B_normalized.npy', allow_pickle=False), 144, min_rows=2)
    ms, fs = load_stats(directory / 'moment_normalization_stats.npz'), load_stats(directory / 'final_normalization_stats.npz')
    for stats, stage in ((ms, 'moments24'), (fs, 'final144')):
        validate_stats(stats, stage)
        if int(stats['fit_count']) != len(rows) or str(stats['fit_manifest_sha256']) != digest(directory / 'fit_manifest.csv'):
            raise ValueError('B v2 fit provenance mismatch')
    if raw.shape != z.shape or after.shape != z.shape or len(rows) != len(z):
        raise ValueError('B v2 gallery dimensions disagree')
    expected = assemble_after_moments(raw[:, :72], raw[:, 72:], ms)
    if not np.array_equal(after, expected) or not np.array_equal(z, apply_stage(after, fs, 'final144')):
        raise ValueError('B v2 saved stages disagree with the matching statistics')
    return rows, z, ms, fs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    print(json.dumps(build(parser.parse_args().output), indent=2))


if __name__ == '__main__':
    main()
