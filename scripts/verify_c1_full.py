"""Full C1 numerical verification and A/B/trial regressions; preserves old data."""
from pathlib import Path
from collections import Counter, defaultdict
import io
import json
import math
import sys
import unittest

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src import lbp236 as kernel
from features.C1_lbp.src.full_v04 import OUT, protected_baseline, read_csv, write_json
from features.C1_lbp.verification import scalar_oracle as oracle
from retrieval.search_c1 import C1Gallery

SAMPLES = ['cfd_final_00001', 'cfd_final_00069', 'hf_merged_00001',
           'hf_merged_00069', 'hf_merged_00198', 'hf_merged_00267', 'hf_merged_00463',
           'hf_merged_00209', 'hf_merged_00333', 'hf_merged_00561', 'hf_merged_00694', 'hf_merged_00722']


def chi_scalar(a, b):
    return .5 * math.fsum((float(x) - float(y)) ** 2 / (float(x) + float(y) + 1e-8) for x, y in zip(a, b))


def main():
    if (OUT / 'verification.json').exists(): raise FileExistsError('Completed verification exists')
    modules = ['test_report_v2.py','test_search_ab.py','test_color_features.py','test_color_report_compliance.py',
               'test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py']
    suite = unittest.TestSuite()
    for filename in modules: suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=filename))
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    with (OUT / 'evidence/regression_tests.log').open('x', encoding='utf-8') as stream: stream.write(log.getvalue())
    print(log.getvalue(), end='', flush=True)
    write_json(OUT / 'evidence/regression_tests.json', dict(tests_run=tests.testsRun, failures=len(tests.failures),
               errors=len(tests.errors), skipped=len(tests.skipped), successful=tests.wasSuccessful(), modules=modules))
    if not tests.wasSuccessful() or tests.skipped: raise AssertionError('Regression tests did not all pass')
    gallery = C1Gallery()
    matrix = gallery.matrix
    counts = np.load(OUT / 'counts.npy', allow_pickle=False)
    eligible = np.load(OUT / 'eligible_centres.npy', allow_pickle=False)
    assert counts.shape == (len(matrix), 4, 59) and counts.dtype == np.uint64
    assert eligible.shape == (len(matrix), 4) and eligible.dtype == np.uint64
    assert np.all(eligible >= 64)
    np.testing.assert_array_equal(counts.sum(axis=2), eligible)
    np.testing.assert_array_equal(matrix.reshape(-1,4,59), counts.astype(np.float64) / eligible[...,None])
    assert gallery.manifest['processed_images'] == 1438
    diagnostics = [json.loads(line) for line in (OUT / 'image_diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(diagnostics) == 1438 and len({r['image_id'] for r in diagnostics}) == 1438
    for record in diagnostics:
        if record['status'] != 'valid_C1':
            assert record['missing_reason'] and record['feature_row_index'] == ''
            continue
        index = int(gallery.by_id[record['image_id']]['feature_row_index'])
        assert record['feature_row_index'] == index
        assert [record['regions'][region]['eligible_centres'] for region in kernel.REGIONS] == eligible[index].tolist()
    print('Validated all1438 status records and all5752 count/L1 groups', flush=True)
    np.testing.assert_array_equal(oracle.codebook(), gallery.context.codebook)
    vertices = defaultdict(list)
    for row in read_csv(ROOT / 'outputs/C1_lbp/roi_remediation_v0_4/candidate_vertices.csv'):
        if row['variant'] == 'candidate_v0_4' and row['image_id'] in SAMPLES:
            vertices[(row['image_id'],row['region'])].append((int(row['vertex_order']),float(row['x']),float(row['y'])))
    oracle_rows, tested_centres, tested_raw_codes = [], 0, 0
    max_hist_error = max_neighbour_error = max_distance_error = 0.
    rank_rows = []
    for identity in SAMPLES:
        row = gallery.by_id[identity]; index = int(row['feature_row_index'])
        bgr = cv2.imread(row['image_path'],cv2.IMREAD_UNCHANGED)
        gray = oracle.gray_image(bgr)
        np.testing.assert_array_equal(kernel.grayscale(bgr),gray)
        for j, region in enumerate(kernel.REGIONS):
            points = [(x,y) for _,x,y in sorted(vertices[(identity,region)])]
            mask = oracle.mask_from_vertices(points)
            expected_counts, histogram, centres = oracle.histogram(gray,mask)
            np.testing.assert_array_equal(expected_counts, counts[index,j])
            assert len(centres) == eligible[index,j]
            error = float(np.max(np.abs(histogram - matrix[index].reshape(4,59)[j])))
            assert error == 0.
            selected = centres[::max(1,len(centres)//64)]
            ys = np.array([y for x,y in selected],np.int64); xs = np.array([x for x,y in selected],np.int64)
            expected_words = [oracle.raw_code(gray,x,y) for x,y in selected]
            expected_neighbours = [[n['gp'] for n in oracle.neighbours(gray,x,y)] for x,y in selected]
            np.testing.assert_array_equal(kernel.raw_codes(gray,ys,xs),expected_words)
            neighbour_error = float(np.max(np.abs(kernel.neighbours(gray,ys,xs) - expected_neighbours)))
            assert neighbour_error == 0.
            max_hist_error = max(max_hist_error,error); max_neighbour_error=max(max_neighbour_error,neighbour_error)
            tested_centres += len(centres); tested_raw_codes += len(selected)
            oracle_rows.append(dict(image_id=identity,region=region,scalar_centres=len(centres),
                               counts_mismatches=0,histogram_max_abs_error=error,raw_codes_sampled=len(selected)))
        q = gallery.vector(identity)
        expected_distances = [chi_scalar(q,v) for v in matrix]
        actual_distances = .5*np.sum((matrix-q)**2/(matrix+q+1e-8),axis=1)
        distance_error = float(np.max(np.abs(actual_distances - expected_distances)))
        max_distance_error = max(max_distance_error,distance_error)
        assert distance_error < 1e-14 and expected_distances[index] == actual_distances[index] == 0.
        independent_order = sorted((i for i,r in enumerate(gallery.rows) if r['image_id'] != identity),
                                   key=lambda i:(expected_distances[i],gallery.rows[i]['image_id']))[:5]
        _, results = gallery.search(identity)
        assert [r['image_id'] for r in results] == [gallery.rows[i]['image_id'] for i in independent_order]
        rank_rows.append(dict(image_id=identity, compared_gallery_distances=len(matrix), max_abs_error=distance_error,
                             top5=[r['image_id'] for r in results], self_distance=0.))
        print('Independent oracle and full-gallery Chi-square/ranking:',identity,flush=True)
    stats = {}
    for j, region in enumerate(kernel.REGIONS):
        ns = eligible[:,j]
        stats[region] = dict(min=int(ns.min()), median=float(np.median(ns)),max=int(ns.max()),total=int(ns.sum()),
                             histogram_sum_min=float(matrix.reshape(-1,4,59)[:,j].sum(axis=1).min()),
                             histogram_sum_max=float(matrix.reshape(-1,4,59)[:,j].sum(axis=1).max()))
    baseline = protected_baseline()
    report = dict(schema_id='C1_FULL_V04_NUMERICAL_VERIFICATION_v1', **gallery.context.lock,
        numerical_status='PASS', processed_images=1438, valid_vectors=len(matrix), missing_images=gallery.manifest['missing_images'],
        valid_source_counts=dict(Counter(r['source'] for r in gallery.rows)), vector_shape=list(matrix.shape),
        dtype=str(matrix.dtype), count_dtype=str(counts.dtype), finite=bool(np.isfinite(matrix).all()), nonnegative=bool(np.all(matrix>=0)),
        histogram_groups_verified=len(matrix)*4, all_counts_equal_eligible=True, exact_counts_div_N_reconstruction=True,
        per_region_support_statistics=stats, regressions=dict(tests_run=tests.testsRun,failures=0,errors=0,skipped=0),
        scalar_oracle_images=SAMPLES, scalar_oracle_histograms=len(oracle_rows),scalar_oracle_centres=tested_centres,
        raw_code_samples=tested_raw_codes, raw_code_mismatches=0, counts_mismatches=0,
        max_histogram_abs_error=max_hist_error, max_neighbour_abs_error=max_neighbour_error,
        scalar_chi_distances_compared=len(SAMPLES)*len(matrix), max_chi_abs_error=max_distance_error,
        scalar_chi_rankings=rank_rows, oracle_histogram_records=oracle_rows,
        tie_break='distance ascending then image_id ascending; duplicate zero-distance candidates retained',
        vector_sum_min=float(matrix.sum(axis=1).min()), vector_sum_max=float(matrix.sum(axis=1).max()),
        protected_existing_files=len(baseline), changed_or_missing_existing_files=[],
        anatomy_status='PROVISIONAL; no anatomical compliance certification', SQLite_writes=0, C2_or_fusion=False)
    write_json(OUT/'verification.json', report)
    print('PASS:',tests.testsRun,'tests;',tested_centres,'scalar centres; Chi-square error',max_distance_error,flush=True)


if __name__ == '__main__': main()
