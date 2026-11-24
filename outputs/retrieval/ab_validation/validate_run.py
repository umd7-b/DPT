"""Read-only independent audit of the actual A/B trial outputs."""
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
A = ROOT / 'outputs/A_geometry/features'
B = ROOT / 'outputs/B_color/color_features_full_v1'
OUT = ROOT / 'outputs/retrieval/ab_experiment'


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


a_rows, b_rows = read(A / 'metadata.csv'), read(B / 'feature_rows.csv')
av = np.load(A / 'features_A_normalized.npy', allow_pickle=False).astype(np.float64)
bv = np.load(B / 'features_B_normalized.npy', allow_pickle=False).astype(np.float64)
ai = {Path(row['image_name']).stem: i for i, row in enumerate(a_rows)}
bi = {row['image_id']: int(row['feature_row_index']) for row in b_rows}
params = load(OUT / 'calibration/median_params.json')
pairs = read(OUT / 'calibration/representative_pairs.csv')
pair_ids = [(row['image_id_1'], row['image_id_2']) for row in pairs]
assert len(set(pair_ids)) == len(pairs) == 20000
assert all(i < j for i, j in pair_ids)
median_errors = {}
for name, matrix, lookup in [('a', av, ai), ('b', bv, bi)]:
    left = np.array([lookup[i] for i, _ in pair_ids])
    right = np.array([lookup[j] for _, j in pair_ids])
    distances = np.linalg.norm(matrix[left] - matrix[right], axis=1)
    saved = np.array([float(row['distance_' + name]) for row in pairs])
    np.testing.assert_array_equal(saved, distances)
    median_errors[name] = abs(float(np.median(distances)) - params['median_' + name])
    assert median_errors[name] == 0

query = load(OUT / 'queries/cfd_final_00001/results.json')
assert query['status'] == 'valid' and query['calibration_reused']
assert query['query_info']['source'] == 'saved_normalized_vectors'
assert query['common_gallery_count'] == 1437
assert query['excluded_self_ids'] == ['cfd_final_00001']
ids = sorted(set(ai) & set(bi))
names = np.array([key + '.png' for key in ids])
da = np.linalg.norm(av[[ai[key] for key in ids]] - av[ai['cfd_final_00001']], axis=1)
db = np.linalg.norm(bv[[bi[key] for key in ids]] - bv[bi['cfd_final_00001']], axis=1)
na = da / (params['median_a'] + params['epsilon'])
nb = db / (params['median_b'] + params['epsilon'])
total = .5 * na + .5 * nb
for mode, scores in [('ab', total), ('a_only', na), ('b_only', nb)]:
    selected = [i for i in np.lexsort((names, scores)) if ids[i] != 'cfd_final_00001'][:5]
    assert [row['image_name'] for row in query['results'][mode]] == names[selected].tolist()
    for index, row in zip(selected, query['results'][mode]):
        assert row['distance_a'] == da[index]
        assert row['distance_b'] == db[index]
        assert row['distance_total'] == total[index]

missing = load(OUT / 'queries/hf_merged_00209/results.json')
assert missing['status'] == 'missing_B'
assert missing['results']['ab'] == missing['results']['b_only'] == []
assert len(missing['results']['a_only']) == 5
assert all(row['distance_b'] is None and row['distance_total'] is None
           for row in missing['results']['a_only'])
assert all(row['image_id'] != 'hf_merged_00209'
           for rows in query['results'].values() for row in rows)

new = load(OUT / 'queries/new_query/results.json')
assert new['query_info']['source'] == 'separate_environment_workers'
assert '.venv311' in Path(new['query_info']['a']['python_executable']).parts
assert '.venv-uniface' in Path(new['query_info']['b']['python_executable']).parts
qa = np.load(OUT / 'queries/new_query/query_A_normalized.npy', allow_pickle=False)
qb = np.load(OUT / 'queries/new_query/query_B_normalized.npy', allow_pickle=False)
a_error = float(np.max(np.abs(qa - av[ai['cfd_final_00001']])))
b_error = float(np.max(np.abs(qb - bv[bi['cfd_final_00001']])))
np.testing.assert_allclose(qa, av[ai['cfd_final_00001']], rtol=1e-6, atol=2e-6)
np.testing.assert_allclose(qb, bv[bi['cfd_final_00001']], rtol=0, atol=1e-10)
preview = cv2.imread(query['preview'])
assert preview is not None and preview.shape == (1098, 1536, 3)
for name in ['unit_tests_uniface.log', 'unit_tests_venv311.log']:
    log = (HERE / name).read_text(encoding='utf-8')
    assert 'Ran 17 tests' in log and 'OK' in log

before = load(HERE / 'protected_before.json')
changed = [name for name, expected in before.items() if sha(ROOT / name) != expected]
assert not changed, changed
summary = dict(status='PASS', protected_files_checked=len(before), changed_protected_files=changed,
               query='cfd_final_00001.png', gallery_a=1438, gallery_b=1437,
               representative_pairs=len(pairs), median_a=params['median_a'], median_b=params['median_b'],
               source_pair_counts=params['source_pair_counts'], independent_median_errors=median_errors,
               independent_top5_recomputation='all three rankings and component distances exact',
               tests_per_environment=17, environments=['.venv311', '.venv-uniface'],
               missing_b_policy='verified: no B vector/distance or combined ranking invented',
               new_query_a_max_absolute_error=a_error, new_query_b_max_absolute_error=b_error,
               new_query_executables={key: new['query_info'][key]['python_executable'] for key in ('a', 'b')},
               preview_shape=list(preview.shape), report_sha256=sha(Path('C:/Users/USER/Downloads/csdldpt.pdf')))
(HERE / 'validation_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
