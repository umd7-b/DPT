"""Fresh, independent numeric recheck; no writes to any v1/v2 directory."""
from pathlib import Path
import json
import math
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_json, read_csv, load_stats, write_json

E = ROOT / 'docs/audits/pre_c_evidence'
A = ROOT / 'outputs/A_geometry/features_report_v2'
B = ROOT / 'outputs/B_color/color_features_report_v2'
AB = ROOT / 'outputs/retrieval/ab_report_v2'


def independent_fit(x):
    mu = np.array([math.fsum(map(float, col)) / len(x) for col in x.T])
    sigma = np.array([math.sqrt(math.fsum((float(v)-m)**2 for v in col) / len(x)) for col, m in zip(x.T, mu)])
    return mu, sigma


def distance(x, y):
    return math.sqrt(math.fsum((float(a)-float(b))**2 for a, b in zip(x, y)))


def main():
    frozen = {}
    for directory in [A, B, AB]:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                frozen[str(path.resolve())] = digest(path)
    for directory, schema in [(A, 'A150_report_v2.0.0'), (B, 'B144_report_v2.0.0')]:
        assert read_json(directory / 'schema.json')['id'] == schema
        for name, expected in read_json(directory / 'gallery_integrity.json').items():
            assert digest(directory / name) == expected
    ar, br = read_csv(A / 'metadata.csv'), read_csv(B / 'feature_rows.csv')
    ai = {r['image_id']: int(r['a_row_index']) for r in ar}
    bi = {r['image_id']: int(r['feature_row_index']) for r in br}
    ax = np.load(read_json(A / 'raw_reference.json')['path'], allow_pickle=False).astype(np.float64)
    av = np.load(A / 'features_A_normalized.npy', allow_pickle=False)
    ast = load_stats(A / 'normalization_stats.npz')
    am, asi = independent_fit(ax)
    ae = float(np.max(abs(av-(ax-am)/(asi+1e-8))))
    assert ae < 1e-10 and float(ast['epsilon']) == 1e-8
    np.testing.assert_array_equal(ast['effective_divisor'], ast['raw_sigma'] + 1e-8)
    bx = np.load(B / 'features_B_raw.npy', allow_pickle=False)
    mid = np.load(B / 'features_B_after_moments.npy', allow_pickle=False)
    bv = np.load(B / 'features_B_normalized.npy', allow_pickle=False)
    ms, fs = load_stats(B / 'moment_normalization_stats.npz'), load_stats(B / 'final_normalization_stats.npz')
    moments = list(range(48, 60)) + list(range(120, 132))
    mm, msi = independent_fit(bx[:, moments])
    expected_mid = bx.copy(); expected_mid[:, moments] = (bx[:, moments]-mm)/np.where(msi<1e-8, 1., msi)
    fm, fsi = independent_fit(expected_mid)
    be = float(np.max(abs(bv-(expected_mid-fm)/np.where(fsi<1e-8, 1., fsi))))
    me = float(np.max(abs(mid-expected_mid)))
    assert me < 1e-10 and be < 1e-10
    assert ms['mean'].shape == (24,) and fs['mean'].shape == (144,)
    for stats in [ms, fs]:
        np.testing.assert_array_equal(stats['effective_divisor'], np.where(stats['raw_sigma']<1e-8, 1., stats['raw_sigma']))
    params = read_json(AB / 'calibration/median_params.json')
    assert params['schema_id'] == 'AB_report_v2.0.0'
    assert float(params['epsilon']) == 1e-8
    for name, expected in params['fingerprint'].items():
        assert digest(name) == expected
    pairs = read_csv(AB / 'calibration/representative_pairs.csv')
    old_pairs = read_csv(ROOT / 'outputs/retrieval/ab_experiment/calibration/representative_pairs.csv')
    assert [(r['image_id_1'], r['image_id_2']) for r in pairs] == [(r['image_id_1'], r['image_id_2']) for r in old_pairs]
    da, db = [], []
    for row in pairs:
        i, j = row['image_id_1'], row['image_id_2']
        a, b = distance(av[ai[i]], av[ai[j]]), distance(bv[bi[i]], bv[bi[j]])
        assert abs(a-float(row['distance_a'])) < 1e-10 and abs(b-float(row['distance_b'])) < 1e-10
        da.append(a); db.append(b)
    assert abs(float(np.median(da))-params['median_a'])<1e-12
    assert abs(float(np.median(db))-params['median_b'])<1e-12
    ids = sorted(bi)
    ranking_cases = 0
    for q in ['cfd_final_00001', 'cfd_final_00088', 'cfd_final_00144']:
        saved = read_json(AB / 'queries' / q / 'results.json')
        qa, qb = av[ai[q]], bv[bi[q]]
        da = np.array([distance(av[ai[key]], qa) for key in ids])
        db = np.array([distance(bv[bi[key]], qb) for key in ids])
        na, nb = da/(params['median_a']+params['epsilon']), db/(params['median_b']+params['epsilon'])
        for mode, scores in [('ab', .5*na+.5*nb), ('a_only', na), ('b_only', nb)]:
            top = sorted((i for i,key in enumerate(ids) if key!=q), key=lambda i: (scores[i], ids[i]))[:5]
            assert [ids[i] for i in top] == [r['image_id'] for r in saved['results'][mode]]
            for index, row in zip(top, saved['results'][mode]):
                assert abs(row['score']-scores[index]) < 1e-10
            ranking_cases += 1
    # Real new-query outputs created ONLY in this audit evidence directory.
    qa = np.load(E / 'new_query_a/query_A_normalized.npy', allow_pickle=False)
    qax = np.load(E / 'new_query_a/query_A_raw.npy', allow_pickle=False)
    qb = np.load(E / 'new_query_b/query_B_normalized.npy', allow_pickle=False)
    qbx = np.load(E / 'new_query_b/query_B_raw.npy', allow_pickle=False)
    qmid = np.load(E / 'new_query_b/query_B_after_moments.npy', allow_pickle=False)
    a_status = read_json(E / 'new_query_a/a_status.json')
    b_status = read_json(E / 'new_query_b/b_status.json')
    assert a_status['schema_id'] == 'A150_report_v2.0.0' and not a_status['query_refit']
    assert b_status['schema_id'] == 'B144_report_v2.0.0' and not b_status['query_refit']
    assert a_status['stats_sha256'] == digest(A / 'normalization_stats.npz')
    assert b_status['moment_stats_sha256'] == digest(B / 'moment_normalization_stats.npz')
    assert b_status['final_stats_sha256'] == digest(B / 'final_normalization_stats.npz')
    assert '.venv311' in Path(a_status['python_executable']).parts
    assert '.venv-uniface' in Path(b_status['python_executable']).parts
    assert np.max(abs(qa-(qax-am)/(asi+1e-8))) < 1e-10
    expect_mid = qbx.copy(); expect_mid[moments] = (qbx[moments]-mm)/np.where(msi<1e-8, 1., msi)
    assert np.max(abs(qmid-expect_mid)) < 1e-10
    assert np.max(abs(qb-(expect_mid-fm)/np.where(fsi<1e-8, 1., fsi))) < 1e-10
    assert np.array_equal(qa, av[0]) and np.array_equal(qb, bv[0])
    missing = read_json(AB / 'queries/hf_merged_00209/results.json')
    assert missing['status']=='missing_B' and not missing['results']['ab'] and not missing['results']['b_only']
    for name, expected in frozen.items():
        assert digest(name) == expected
    write_json(E / 'v2_freeze_manifest.json', dict(status='FROZEN_UNCHANGED', files=frozen,
        schema_versions=params['feature_versions'], calibration_schema=params['schema_id'],
        median_a=params['median_a'], median_b=params['median_b'], pair_ids_sha256=params['pair_ids_sha256'],
        a_matrix_shape=list(av.shape), b_matrix_shape=list(bv.shape),
        a_full_oracle_error=ae, b_moment_oracle_error=me, b_full_oracle_error=be,
        pair_count=len(pairs), ranking_cases_verified=ranking_cases,
        new_query_real_workers_verified=True, missing_B_verified=True,
        caveat='Numerical freeze does not certify anatomical mapping, input dataset or database implementation'))
    print(json.dumps(dict(status='PASS', frozen_v2_files=len(frozen), a_error=ae, b_error=be,
                         pair_count=len(pairs), ranking_cases=ranking_cases, new_query=True), indent=2))


if __name__=='__main__':
    main()
