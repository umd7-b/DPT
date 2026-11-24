"""Independent output verification for the exact100 provisional C1 trial."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import random
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src import lbp236 as target
from features.C1_lbp.src.gallery import TrialGallery
from features.C1_lbp.src.trial100 import OUT, inputs, read_csv, write_json
from features.C1_lbp.verification import scalar_oracle as oracle


def main():
    evidence = OUT / 'evidence'
    if (evidence / 'numerical_verification.json').exists():
        raise FileExistsError('Completed verification exists; no overwrite')
    context = target.Context()
    gallery = TrialGallery(OUT, context)
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))['images']
    plan = json.loads((target.SPEC_DIR / 'trial100_manifest.json').read_text(encoding='utf-8'))['images']
    assert [(r['image_id'], r['source']) for r in manifest] == [(r['image_id'], r['source']) for r in plan]
    counts = np.load(OUT / 'counts.npy', allow_pickle=False)
    histograms = np.load(OUT / 'histograms.npy', allow_pickle=False)
    assert counts.dtype == np.uint64 and counts.shape == (len(gallery.rows), 4, 59)
    assert histograms.dtype == np.float64 and histograms.shape == counts.shape
    assert np.array_equal(gallery.vectors, histograms.reshape(-1, 236))
    uniform = oracle.codebook()
    assert np.array_equal(uniform, context.codebook)
    expected = {r['image_id']: r for r in manifest}
    frozen = {(r['image_id'], r['region']): r for r in read_csv(target.SPEC_DIR / 'metrics.csv')}
    images, landmarks = inputs()
    records = {}
    for row in manifest:
        identity = row['image_id']
        record = json.loads((OUT / 'images' / (identity + '.json')).read_text(encoding='utf-8'))
        context.require_lock(record)
        assert record['image_id'] == identity and record['status'] == row['status']
        assert record['image_sha256'] == images[identity]['image_hash']
        assert record['landmark_row_sha256'] == hashlib.sha256(landmarks[identity][1].tobytes()).hexdigest()
        records[identity] = record
        for region in target.REGIONS:
            measured, old = record['regions'][region], frozen[(identity, region)]
            assert measured['raw_mask_pixels'] == int(old['raw_mask_pixels'])
            assert measured['eligible_centres'] == int(old['support_valid_centres'])
            assert measured['raw_mask_sha256'] == old['raw_mask_sha256']
        if row['status'] == 'missing_C1':
            assert record['vector'] is None and record['counts'] is None and record['histograms'] is None
            assert row['feature_row_index'] is None and record['missing_reason']
            assert identity not in gallery.rows
            continue
        feature_row = gallery.rows[identity]
        vector = gallery.vector(identity)
        np.testing.assert_array_equal(vector, record['vector'])
        np.testing.assert_array_equal(counts[feature_row], record['counts'])
        np.testing.assert_array_equal(histograms[feature_row], record['histograms'])
        for j, region in enumerate(target.REGIONS):
            n = record['regions'][region]['eligible_centres']
            assert int(counts[feature_row, j].sum()) == n
            np.testing.assert_array_equal(histograms[feature_row, j], counts[feature_row, j].astype(np.float64) / n)
        query = gallery.extract_query(cv2.imread(images[identity]['image_path']), landmarks[identity][1], identity, row['source'])
        np.testing.assert_array_equal(query['vector'], vector)
        assert target.chi_square(vector, query['vector']) == 0.
    print('All100 serialized records; gallery round-trip and same query path verified', flush=True)

    # Selection fixed before numerical comparisons, independent of retrieval outputs.
    subset = ['cfd_final_00001', 'hf_merged_00209', 'hf_merged_00333', 'hf_merged_00561', 'hf_merged_00694', 'hf_merged_00722']
    rng = random.Random(6112026)
    for source in ('cfd', 'hf'):
        candidates = sorted(r['image_id'] for r in manifest if r['source'] == source
                            and r['status'] == 'valid_C1' and r['image_id'] not in subset)
        subset.extend(rng.sample(candidates, 2))
    vertices = {}
    for row in read_csv(target.SPEC_DIR / 'roi_vertices.csv'):
        if row['image_id'] in subset:
            vertices.setdefault((row['image_id'], row['region']), []).append((int(row['vertex_order']), float(row['x']), float(row['y'])))
    oracle_rows, hand, tested_centres = [], None, 0
    max_hist_error = max_neighbour_error = 0.
    for identity in subset:
        bgr = cv2.imread(images[identity]['image_path'], cv2.IMREAD_UNCHANGED)
        gray = oracle.gray_image(bgr)
        np.testing.assert_array_equal(target.grayscale(bgr), gray)
        for j, region in enumerate(target.REGIONS):
            saved_vertices = [(x, y) for _, x, y in sorted(vertices[(identity, region)])]
            mask = oracle.mask_from_vertices(saved_vertices)
            frozen_row = frozen[(identity, region)]
            assert hashlib.sha256(mask.tobytes()).hexdigest() == frozen_row['raw_mask_sha256']
            selected = oracle.centres(mask)
            assert len(selected) == int(frozen_row['support_valid_centres'])
            expected_counts = [0] * 59
            scalar_words, scalar_neighbours = [], []
            for x, y in selected:
                samples = oracle.neighbours(gray, x, y)
                word = sum(item['bit'] * (1 << p) for p, item in enumerate(samples))
                scalar_words.append(word); scalar_neighbours.append([item['gp'] for item in samples])
                expected_counts[uniform[word]] += 1
            xs = np.array([x for x, _ in selected], dtype=np.int64)
            ys = np.array([y for _, y in selected], dtype=np.int64)
            # Expected arrays above never use target helpers.
            actual_words = target.raw_codes(gray, ys, xs)
            actual_neighbours = target.neighbours(gray, ys, xs)
            np.testing.assert_array_equal(actual_words, scalar_words)
            neighbour_error = float(np.max(np.abs(actual_neighbours - scalar_neighbours)))
            np.testing.assert_array_equal(actual_neighbours, scalar_neighbours)
            row_index = gallery.rows[identity]
            np.testing.assert_array_equal(counts[row_index, j], expected_counts)
            expected_hist = np.array([v / len(selected) for v in expected_counts], dtype=np.float64)
            histogram_error = float(np.max(np.abs(histograms[row_index, j] - expected_hist)))
            np.testing.assert_array_equal(histograms[row_index, j], expected_hist)
            max_hist_error = max(max_hist_error, histogram_error)
            max_neighbour_error = max(max_neighbour_error, neighbour_error)
            tested_centres += len(selected)
            oracle_rows.append(dict(image_id=identity, region=region, eligible_centres=len(selected),
                               raw_code_mismatches=0, counts_mismatches=0, max_histogram_abs_error=histogram_error,
                               max_neighbour_abs_error=neighbour_error))
            if hand is None:
                x, y = selected[len(selected) // 2]
                samples = oracle.neighbours(gray, x, y)
                word = sum(item['bit'] * (1 << p) for p, item in enumerate(samples))
                hand = dict(image_id=identity, region=region, center_xy=[x, y], center_BGR=bgr[y, x].tolist(),
                            gc=float(gray[y, x]), neighbours=samples, raw_code=word, bin=uniform[word],
                            selection='middle row-major eligible centre in first fixed subset image/region; no ranking')
        print('Independent scalar oracle:', identity, flush=True)

    region_stats = {}
    valid_records = [records[r['image_id']] for r in manifest if r['status'] == 'valid_C1']
    for j, region in enumerate(target.REGIONS):
        ns = [r['regions'][region]['eligible_centres'] for r in valid_records]
        raw = [r['regions'][region]['raw_mask_pixels'] for r in valid_records]
        region_stats[region] = dict(raw_mask_min=min(raw), raw_mask_max=max(raw), centres_min=min(ns),
            centres_max=max(ns), centres_total=sum(ns), histogram_sum_min=float(histograms[:, j].sum(axis=1).min()),
            histogram_sum_max=float(histograms[:, j].sum(axis=1).max()),
            occupied_bins_min=int(np.count_nonzero(counts[:, j], axis=1).min()),
            occupied_bins_max=int(np.count_nonzero(counts[:, j], axis=1).max()))
    result = dict(context.lock, numerical_status='PASS', input_count=len(manifest), valid_count=len(gallery.rows),
                  missing_count=len(manifest) - len(gallery.rows), source_counts=dict(Counter(r['source'] for r in manifest)),
                  all_serialized_vectors_validated=len(gallery.rows), query_gallery_bitwise_comparisons=len(gallery.rows),
                  geometry_against_frozen_audit=400, scalar_subset_seed=6112026, scalar_subset=subset,
                  scalar_histograms=len(oracle_rows), scalar_centres=tested_centres,
                  max_histogram_abs_error=max_hist_error, max_neighbour_abs_error=max_neighbour_error,
                  raw_code_mismatches=0, counts_mismatches=0, uniform_patterns=58, nonuniform_patterns=198,
                  vector_dtype=str(gallery.vectors.dtype), counts_dtype=str(counts.dtype),
                  vector_sum_min=float(gallery.vectors.sum(axis=1).min()), vector_sum_max=float(gallery.vectors.sum(axis=1).max()),
                  region_statistics=region_stats, oracle_details=oracle_rows,
                  anatomy='UNVERIFIED; numerical pass does not certify anatomical ROIs', rankings_computed=0)
    write_json(evidence / 'hand_calculation.json', dict(context.lock, **hand))
    write_json(evidence / 'numerical_verification.json', result)
    print('PASS:', tested_centres, 'scalar centres,', len(oracle_rows), 'histograms; max error', max_hist_error, flush=True)


if __name__ == '__main__':
    main()
