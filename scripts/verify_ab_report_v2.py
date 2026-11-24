"""Independent v2 acceptance oracle; reads official artifacts, writes new evidence.

No fit/transform/rank/calibration implementation is called to derive expectations.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_csv, save_csv, write_json, read_json, load_stats

A0 = ROOT / 'outputs/A_geometry/features'
B0 = ROOT / 'outputs/B_color/color_features_full_v1'
OLD = ROOT / 'outputs/retrieval/ab_experiment'
A = ROOT / 'outputs/A_geometry/features_report_v2'
B = ROOT / 'outputs/B_color/color_features_report_v2'
AB = ROOT / 'outputs/retrieval/ab_report_v2'
E = ROOT / 'docs/audits/v2_evidence'


def independent_fit(matrix):
    n = len(matrix)
    mean = np.array([math.fsum(map(float, column)) / n for column in matrix.T])
    sigma = np.array([math.sqrt(math.fsum((float(x) - m) ** 2 for x in col) / n)
                      for col, m in zip(matrix.T, mean)])
    return mean, sigma


def euclidean(left, right):
    return math.sqrt(math.fsum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def maximum_error(actual, expected, atol=1e-10):
    value = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    assert value <= atol, (value, atol)
    return value


def ordered(ids, scores, excluded):
    return sorted((i for i, key in enumerate(ids) if key not in excluded), key=lambda i: (scores[i], ids[i] + '.png'))


def main():
    started = time.perf_counter()
    ax = np.load(A0 / 'features_A_raw.npy', allow_pickle=False).astype(np.float64)
    old_a = np.load(A0 / 'features_A_normalized.npy', allow_pickle=False).astype(np.float64)
    az = np.load(A / 'features_A_normalized.npy', allow_pickle=False)
    ast = load_stats(A / 'normalization_stats.npz')
    ar = read_csv(A / 'metadata.csv')
    assert read_json(A / 'schema.json')['id'] == 'A150_report_v2.0.0'
    assert ax.shape == az.shape == (1438, 150) and az.dtype == np.float64
    assert np.isfinite(az).all()
    am, asi = independent_fit(ax)
    a_oracle = (ax - am) / (asi + 1e-8)
    a_error = maximum_error(az, a_oracle)
    maximum_error(ast['mean'], am)
    maximum_error(ast['raw_sigma'], asi)
    maximum_error(ast['effective_divisor'], asi + 1e-8)
    assert float(ast['epsilon']) == 1e-8 and int(ast['ddof']) == 0
    assert int(ast['fit_count']) == 1438
    raw_ref = read_json(A / 'raw_reference.json')
    assert raw_ref['sha256'] == digest(A0 / 'features_A_raw.npy')
    assert digest(raw_ref['path']) == raw_ref['sha256']

    bx = np.load(B / 'features_B_raw.npy', allow_pickle=False)
    old_bx = np.load(B0 / 'features_B_raw.npy', allow_pickle=False)
    old_b = np.load(B0 / 'features_B_normalized.npy', allow_pickle=False)
    intermediate = np.load(B / 'features_B_after_moments.npy', allow_pickle=False)
    bz = np.load(B / 'features_B_normalized.npy', allow_pickle=False)
    ms = load_stats(B / 'moment_normalization_stats.npz')
    fs = load_stats(B / 'final_normalization_stats.npz')
    br = read_csv(B / 'feature_rows.csv')
    manifest = read_csv(B / 'manifest.csv')
    assert read_json(B / 'schema.json')['id'] == 'B144_report_v2.0.0'
    assert bx.shape == intermediate.shape == bz.shape == (1437, 144)
    assert np.array_equal(bx, old_bx) and np.isfinite(bz).all()
    assert len(manifest) == 1438 and len(br) == 1437
    assert [r['image_name'] for r in manifest] == [r['image_name'] for r in ar]
    moments = np.array([48 + i for i in range(12)] + [120 + i for i in range(12)])
    mm, msi = independent_fit(bx[:, moments])
    md = np.array([1. if x < 1e-8 else x for x in msi])
    expected_intermediate = bx.copy()
    expected_intermediate[:, moments] = (bx[:, moments] - mm) / md
    moment_error = maximum_error(intermediate, expected_intermediate)
    nonmoment = [j for j in range(144) if j not in moments]
    assert np.array_equal(intermediate[:, nonmoment], bx[:, nonmoment])
    fm, fsi = independent_fit(expected_intermediate)
    fd = np.array([1. if x < 1e-8 else x for x in fsi])
    final_oracle = (expected_intermediate - fm) / fd
    b_error = maximum_error(bz, final_oracle)
    maximum_error(ms['mean'], mm); maximum_error(ms['raw_sigma'], msi); maximum_error(ms['effective_divisor'], md)
    maximum_error(fs['mean'], fm); maximum_error(fs['raw_sigma'], fsi); maximum_error(fs['effective_divisor'], fd)
    for stats, stage, dim in [(ms, 'moments24', 24), (fs, 'final144', 144)]:
        assert str(stats['schema_id']) == 'B144_report_v2.0.0' and str(stats['stage']) == stage
        assert int(stats['dimension']) == dim and int(stats['ddof']) == 0 and int(stats['fit_count']) == 1437
        assert str(stats['fit_manifest_sha256']) == digest(B / 'fit_manifest.csv')

    # Record all numeric stage statistics and before/after divisors.
    old_as, old_bs = load_stats(A0 / 'geometry_stats.npz'), load_stats(B0 / 'normalization_stats.npz')
    stat_rows = []
    for stage, stats, previous in [('a150', ast, old_as), ('b_lab24', ms, None), ('b_final144', fs, old_bs)]:
        for j in range(len(stats['mean'])):
            stat_rows.append(dict(stage=stage, dimension_index=j, v1_mean=None if previous is None else float(previous['mean'][j]),
                v1_effective_divisor=None if previous is None else float(previous['std'][j]),
                v2_mean=float(stats['mean'][j]), v2_raw_sigma=float(stats['raw_sigma'][j]),
                v2_effective_divisor=float(stats['effective_divisor'][j]),
                note='B final moments use transformed units, not original raw Lab units' if stage == 'b_final144' else ''))
    save_csv(E / 'normalization_stats_comparison.csv', stat_rows)

    ai = {r['image_id']: int(r['a_row_index']) for r in ar}
    bi = {r['image_id']: int(r['feature_row_index']) for r in br}
    assert len(ai) == 1438 and len(bi) == 1437
    for row in br:
        assert ar[int(row['a_row_index'])]['image_id'] == row['image_id']
    missing = read_csv(B / 'missing_features.csv')
    assert len(missing) == 1 and missing[0]['image_id'] == 'hf_merged_00209' and missing[0]['feature_row_index'] == ''
    for key in ['hf_merged_00333', 'hf_merged_00561', 'hf_merged_00722']:
        assert key in ai and key in bi  # Flagged examples were not removed to improve rankings.

    old_params = read_json(OLD / 'calibration/median_params.json')
    params = read_json(AB / 'calibration/median_params.json')
    pairs = read_csv(AB / 'calibration/representative_pairs.csv')
    old_pairs = read_csv(OLD / 'calibration/representative_pairs.csv')
    identities = [(r['image_id_1'], r['image_id_2']) for r in pairs]
    assert identities == [(r['image_id_1'], r['image_id_2']) for r in old_pairs]
    assert len(set(identities)) == len(pairs) == 20000 and all(i < j for i, j in identities)
    assert params['schema_id'] == 'AB_report_v2.0.0'
    assert params['feature_versions'] == dict(a='A150_report_v2.0.0', b='B144_report_v2.0.0')
    expected_ids_hash = hashlib.sha256(json.dumps(identities, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
    assert params['pair_ids_sha256'] == expected_ids_hash
    assert params['source_pairs_sha256'] == digest(OLD / 'calibration/representative_pairs.csv')
    assert params['pairs_sha256'] == digest(AB / 'calibration/representative_pairs.csv')
    assert float(params['epsilon']) == 1e-8
    for name, expected in params['fingerprint'].items():
        p = Path(name).resolve()
        assert A.resolve() in p.parents or B.resolve() in p.parents
        assert digest(p) == expected
    pair_a, pair_b = [], []
    pair_a_error, pair_b_error = 0., 0.
    for row in pairs:
        i, j = row['image_id_1'], row['image_id_2']
        da, db = euclidean(az[ai[i]], az[ai[j]]), euclidean(bz[bi[i]], bz[bi[j]])
        pair_a_error = max(pair_a_error, abs(da - float(row['distance_a'])))
        pair_b_error = max(pair_b_error, abs(db - float(row['distance_b'])))
        pair_a.append(da); pair_b.append(db)
    median_a, median_b = float(np.median(pair_a)), float(np.median(pair_b))
    assert abs(median_a - params['median_a']) < 1e-12 and abs(median_b - params['median_b']) < 1e-12

    ids = sorted(bi)
    distances_out, top_comparison, rank_summary = [], [], []
    for query_id in ['cfd_final_00001', 'cfd_final_00088', 'cfd_final_00144']:
        result = read_json(AB / 'queries' / query_id / 'results.json')
        assert result['feature_versions'] == params['feature_versions']
        assert result['excluded_self_ids'] == [query_id] and result['status'] == 'valid'
        da = np.array([euclidean(az[ai[key]], az[ai[query_id]]) for key in ids])
        db = np.array([euclidean(bz[bi[key]], bz[bi[query_id]]) for key in ids])
        oda = np.array([euclidean(old_a[ai[key]], old_a[ai[query_id]]) for key in ids])
        odb = np.array([euclidean(old_b[bi[key]], old_b[bi[query_id]]) for key in ids])
        na, nb = da / (params['median_a'] + 1e-8), db / (params['median_b'] + 1e-8)
        ona, onb = oda / (old_params['median_a'] + 1e-8), odb / (old_params['median_b'] + 1e-8)
        total, old_total = .5 * na + .5 * nb, .5 * ona + .5 * onb
        for i, key in enumerate(ids):
            distances_out.append(dict(query_id=query_id, image_id=key, distance_a_v1=float(oda[i]), distance_a_v2=float(da[i]),
                distance_b_v1=float(odb[i]), distance_b_v2=float(db[i]), total_v1=float(old_total[i]), total_v2=float(total[i])))
        for mode, scores, previous in [('ab', total, old_total), ('a_only', na, ona), ('b_only', nb, onb)]:
            all_order = ordered(ids, scores, {query_id}); old_order = ordered(ids, previous, {query_id})
            wanted, old_wanted = all_order[:5], old_order[:5]
            actual = result['results'][mode]
            assert [ids[i] for i in wanted] == [r['image_id'] for r in actual]
            for index, row in zip(wanted, actual):
                assert abs(da[index] - row['distance_a']) < 1e-10
                assert abs(db[index] - row['distance_b']) < 1e-10
                assert abs(total[index] - row['distance_total']) < 1e-10
                assert abs(scores[index] - row['score']) < 1e-10
            rank_summary.append(dict(query_id=query_id, mode=mode, top5_order_changed=wanted != old_wanted,
                whole_ranking_positions_changed=sum(i != j for i, j in zip(all_order, old_order)),
                maximum_score_change=float(np.max(np.abs(scores - previous))),
                old_top5=[ids[i] for i in old_wanted], new_top5=[ids[i] for i in wanted]))
            for rank, (i, j) in enumerate(zip(old_wanted, wanted), 1):
                top_comparison.append(dict(query_id=query_id, mode=mode, rank=rank, v1_image_id=ids[i], v2_image_id=ids[j],
                    v1_score=float(previous[i]), v2_score=float(scores[j]), v1_total=float(old_total[i]), v2_total=float(total[j])))
    save_csv(E / 'distance_comparison.csv', distances_out)
    save_csv(E / 'top5_comparison.csv', top_comparison)
    write_json(E / 'ranking_comparison.json', rank_summary)

    # Full two-stage query test, using outputs of real workers in their original venvs.
    new_dir = AB / 'queries/new_query'
    new_status = read_json(new_dir / 'results.json')
    assert new_status['query_info']['source'] == 'separate_environment_v2_workers'
    assert new_status['calibration_reused']
    assert '.venv311' in Path(new_status['query_info']['a']['python_executable']).parts
    assert '.venv-uniface' in Path(new_status['query_info']['b']['python_executable']).parts
    qax = np.load(new_dir / 'query_A_raw.npy', allow_pickle=False).astype(np.float64)
    qa = np.load(new_dir / 'query_A_normalized.npy', allow_pickle=False)
    qbx = np.load(new_dir / 'query_B_raw.npy', allow_pickle=False)
    qinter = np.load(new_dir / 'query_B_after_moments.npy', allow_pickle=False)
    qb = np.load(new_dir / 'query_B_normalized.npy', allow_pickle=False)
    aq_error = maximum_error(qa, (qax - am) / (asi + 1e-8))
    expected_qinter = qbx.copy(); expected_qinter[moments] = (qbx[moments] - mm) / md
    bq_mid_error = maximum_error(qinter, expected_qinter)
    bq_error = maximum_error(qb, (expected_qinter - fm) / fd)
    assert np.array_equal(qax, ax[0]) and np.array_equal(qbx, bx[0])
    assert np.array_equal(qa, az[0]) and np.array_equal(qb, bz[0])
    missing_result = read_json(AB / 'queries/hf_merged_00209/results.json')
    assert missing_result['status'] == 'missing_B'
    assert not missing_result['results']['ab'] and not missing_result['results']['b_only']
    assert len(missing_result['results']['a_only']) == 5
    assert all(r['distance_b'] is None and r['distance_total'] is None for r in missing_result['results']['a_only'])
    missing_worker = AB / 'query_checks/missing_B_new_worker'
    assert read_json(missing_worker / 'b_status.json')['status'] == 'missing_B' and not list(missing_worker.glob('*.npy'))

    # Additional B-only before/after comparison on all 10 original B evaluation queries.
    b_results = []
    for query_id in sorted({r['query_id'] for r in read_csv(B0 / 'retrieval/top5.csv')}):
        distances = [euclidean(v, bz[bi[query_id]]) for v in bz]
        selected = sorted((i for i, r in enumerate(br) if r['image_id'] != query_id), key=lambda i: (distances[i], br[i]['image_name']))[:5]
        previous = sorted([r for r in read_csv(B0 / 'retrieval/top5.csv') if r['query_id'] == query_id], key=lambda r: int(r['rank']))
        for rank, (old, index) in enumerate(zip(previous, selected), 1):
            b_results.append(dict(query_id=query_id, rank=rank, v1_image_id=old['image_id'], v2_image_id=br[index]['image_id'],
                                  v1_distance=float(old['distance']), v2_distance=distances[index]))
    save_csv(E / 'b_only_10_queries_comparison.csv', b_results)

    # All legacy source, vectors, dataset, audits and PDF must still be byte-identical.
    baseline = read_json(E / 'baseline_before.json')
    changed = [name for name, expected in baseline.items() if not Path(name).is_file() or digest(name) != expected]
    assert not changed, changed
    tests = {}
    for file in ['all_tests_venv311.log', 'uniface_batch_tests.log', 'new_tests_uniface.log', 'old_a_audit_oracles.log', 'old_b_audit_oracles.log']:
        text = (E / file).read_text(encoding='utf-8')
        count = int(re.search(r'Ran (\d+) tests', text).group(1))
        assert 'FAILED (' not in text and 'OK' in text
        skip = re.search(r'OK \(skipped=(\d+)\)', text)
        tests[file] = dict(tests=count, skipped=int(skip.group(1)) if skip else 0, passed=True)
    summary = dict(status='PASS', a12_corrected=True, b12_corrected=True,
        a_shape=list(az.shape), b_shape=list(bz.shape), normalized_dtype='float64',
        a_full_oracle_max_error=a_error, b_moment_stage_max_error=moment_error, b_full_two_stage_oracle_max_error=b_error,
        a_query_oracle_max_error=aq_error, b_query_moment_max_error=bq_mid_error, b_query_final_max_error=bq_error,
        raw_b_exactly_unchanged=True, a_raw_reference_unchanged=True, pair_ids_identical=True, pair_count=len(pairs),
        independent_pair_a_max_error=pair_a_error, independent_pair_b_max_error=pair_b_error,
        median_a_v1=old_params['median_a'], median_a_v2=params['median_a'], median_a_delta=params['median_a']-old_params['median_a'],
        median_b_v1=old_params['median_b'], median_b_v2=params['median_b'], median_b_delta=params['median_b']-old_params['median_b'],
        queried_baselines=3, queried_ranking_modes=9, top5_changed_cases=sum(r['top5_order_changed'] for r in rank_summary),
        whole_ranking_positions_changed=sum(r['whole_ranking_positions_changed'] for r in rank_summary),
        original_b_only_top5_rows_compared=len(b_results), original_b_only_changed_ranks=sum(r['v1_image_id']!=r['v2_image_id'] for r in b_results),
        missing_B_query_verified=True, new_query_two_environments_verified=True, tests=tests,
        legacy_files_hash_checked=len(baseline), changed_legacy_files=changed, c1_c2_unchanged=True,
        dataset_unchanged=True, pdf_sha256=digest('C:/Users/USER/Downloads/csdldpt.pdf'),
        normalization_deviations_in_active_v2='No remaining A12/B12 normalization deviation found by these oracles',
        full_system_compliance=False, caveat='Dataset violations and unresolved geometry/self-match/metadata criteria remain; no relevance-quality claims',
        elapsed_seconds=time.perf_counter()-started)
    write_json(E / 'verification_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
