"""Independent numeric fixtures for experimental A/B distance fusion."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from retrieval import search_ab as ab


def fixture():
    a_rows = [dict(image_name=f'{key}.png', image_path=f'{key}.png') for key in ('a', 'missing', 'b', 'c')]
    a = np.zeros((4, 150))
    a[:, 0] = [0, 999, 3, 6]
    # Deliberately different row ordering, plus the absent A row in the middle.
    b = np.zeros((3, 144))
    b[:, 0] = [8, 0, 4]  # c, a, b
    b_rows = [dict(image_id=key, image_name=f'{key}.png', image_path=f'{key}.png',
                   a_row_index=ai, feature_row_index=bi, source_sha256=key,
                   dataset_source='CFD' if key == 'a' else 'HF', status='valid')
              for key, ai, bi in [('b', 2, 2), ('c', 3, 0), ('a', 0, 1)]]
    return a_rows, a, b_rows, b


def gallery():
    return ab.join_galleries(*fixture())


class ABTests(unittest.TestCase):
    def test_join_uses_identity_and_explicit_feature_index_with_missing_middle_row(self):
        g = gallery()
        self.assertEqual([r['image_id'] for r in g.rows], ['a', 'b', 'c'])
        np.testing.assert_array_equal(g.a[:, 0], [0, 3, 6])
        np.testing.assert_array_equal(g.b[:, 0], [0, 4, 8])
        self.assertEqual([r['image_id'] for r in g.missing_b], ['missing'])
        self.assertEqual(g.a.shape, (3, 150))

    def test_metadata_permutation_does_not_change_calibration_or_ranking(self):
        data = fixture()
        g = ab.join_galleries(*data)
        data[2].reverse()
        other = ab.join_galleries(*data)
        np.testing.assert_array_equal(g.b, other.b)
        with tempfile.TemporaryDirectory() as folder:
            params, _ = ab.calibrate(g, folder, pair_count=100)
            reused_params, reused = ab.calibrate(other, folder, pair_count=100)
        self.assertTrue(reused)
        self.assertEqual(params, reused_params)

    def test_join_rejects_conflicting_a_index_and_duplicate_b_index(self):
        for key, value in [('a_row_index', 1), ('feature_row_index', 0), ('image_id', 'unknown')]:
            data = deepcopy(fixture())
            data[2][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                ab.join_galleries(*data)

    def test_duplicate_identity_and_nonfinite_vectors_are_rejected(self):
        data = deepcopy(fixture())
        data[0][1] = data[0][0]
        with self.assertRaises(ValueError):
            ab.join_galleries(*data)
        data = fixture()
        data[3][0, 0] = np.nan
        with self.assertRaises(ValueError):
            ab.join_galleries(*data)

    def test_same_unordered_nonself_pair_sample_is_reproducible(self):
        pairs = ab.representative_pairs(40, seed=42, pair_count=73)
        np.testing.assert_array_equal(pairs, ab.representative_pairs(40, seed=42, pair_count=73))
        self.assertEqual(len(set(map(tuple, pairs))), 73)
        self.assertTrue(np.all(pairs[:, 0] < pairs[:, 1]))
        self.assertFalse(np.array_equal(pairs, ab.representative_pairs(40, seed=43, pair_count=73)))

    def test_calibration_has_known_medians_from_the_same_three_pairs(self):
        # A distances = 3,6,3 => median 3; B = 4,8,4 => median 4.
        with tempfile.TemporaryDirectory() as folder:
            params, reused = ab.calibrate(gallery(), folder, pair_count=100)
            self.assertFalse(reused)
            self.assertEqual((params['median_a'], params['median_b'], params['pair_count']), (3., 4., 3))
            rows = ab.read_csv(Path(folder) / 'representative_pairs.csv')
            self.assertEqual([(r['image_id_1'], r['image_id_2']) for r in rows], [('a', 'b'), ('a', 'c'), ('b', 'c')])
            _, reused = ab.calibrate(gallery(), folder, pair_count=100)
            self.assertTrue(reused)

    def test_calibration_rejects_stale_fingerprint_and_tampered_pairs(self):
        with tempfile.TemporaryDirectory() as folder:
            g = gallery()
            ab.calibrate(g, folder)
            g.fingerprint = {'changed': 'hash'}
            with self.assertRaisesRegex(ValueError, 'Stale'):
                ab.calibrate(g, folder)
            g.fingerprint = {}
            with (Path(folder) / 'representative_pairs.csv').open('a') as stream:
                stream.write('tampered')
            with self.assertRaisesRegex(ValueError, 'changed'):
                ab.calibrate(g, folder)

    def test_calibration_rejects_tampered_median(self):
        with tempfile.TemporaryDirectory() as folder:
            ab.calibrate(gallery(), folder)
            path = Path(folder) / 'median_params.json'
            params = json.loads(path.read_text())
            params['median_a'] = 700
            ab.write_json(path, params)
            with self.assertRaisesRegex(ValueError, 'disagrees'):
                ab.calibrate(gallery(), folder)

    def test_euclidean_and_report_formula_with_epsilon_in_denominator(self):
        g = gallery()
        qa, qb = np.zeros(150), np.zeros(144)
        qa[1], qb[1] = 4, 3
        params = dict(median_a=2., median_b=4., epsilon=.5)
        result = ab.rankings(g, qa, qb, params, .25, .75)
        b = next(row for row in result['ab'] if row['image_id'] == 'b')
        self.assertEqual(b['distance_a'], 5.)  # sqrt(3^2 + 4^2)
        self.assertEqual(b['distance_b'], 5.)  # sqrt(4^2 + 3^2)
        self.assertAlmostEqual(b['normalized_a'], 5 / 2.5)
        self.assertAlmostEqual(b['distance_total'], .25 * 5 / 2.5 + .75 * 5 / 4.5)
        self.assertNotAlmostEqual(b['distance_total'], np.sqrt(.25 * (5 / 2.5)**2 + .75 * (5 / 4.5)**2))

    def test_baselines_same_candidate_set_self_exclusion_and_top_k(self):
        g = gallery()
        params = dict(median_a=3., median_b=4., epsilon=1e-8)
        result = ab.rankings(g, g.a[0], g.b[0], params, top_k=99, exclude_ids={'a'})
        for rows in result.values():
            self.assertEqual([row['image_id'] for row in rows], ['b', 'c'])
        self.assertEqual(len(ab.rankings(g, g.a[0], g.b[0], params, top_k=1)['ab']), 1)

    def test_weight_endpoints_match_baselines(self):
        g = gallery()
        params = dict(median_a=3., median_b=4., epsilon=1e-8)
        for wa, wb, mode in [(1., 0., 'a_only'), (0., 1., 'b_only')]:
            result = ab.rankings(g, g.a[0], g.b[-1], params, wa, wb)
            self.assertEqual([r['image_id'] for r in result['ab']], [r['image_id'] for r in result[mode]])

    def test_missing_query_b_keeps_a_and_never_creates_zero_distance(self):
        g = gallery()
        result = ab.rankings(g, g.a[0], None, dict(median_a=3., median_b=4., epsilon=1e-8))
        self.assertEqual(result['ab'], [])
        self.assertEqual(result['b_only'], [])
        self.assertTrue(result['a_only'])
        for row in result['a_only']:
            self.assertIsNone(row['distance_b'])
            self.assertIsNone(row['distance_total'])

    def test_ties_are_broken_by_filename(self):
        g = gallery()
        g.a[:] = 1
        g.b[:] = 1
        rows = ab.rankings(g, g.a[0], g.b[0], dict(median_a=0., median_b=0., epsilon=1e-8))['ab']
        self.assertEqual([r['image_name'] for r in rows], ['a.png', 'b.png', 'c.png'])

    def test_invalid_weights_and_top_k_fail(self):
        for weights in [(-.5, 1.5), (0, 0), (.5, .7), (float('nan'), .5), (float('inf'), 0)]:
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                ab.validate_weights(*weights)
        g = gallery()
        with self.assertRaises(ValueError):
            ab.rankings(g, g.a[0], g.b[0], {}, top_k=0)

    def test_existing_query_reuses_vectors_without_spawning_extractors(self):
        g = gallery()
        with patch.object(ab, 'identify_query', return_value=({'b'}, 'sha')), patch.object(ab, 'run_worker') as worker:
            qa, qb, ids, status = ab.query_vectors(Path('b.png'), g, Path('.'))
        worker.assert_not_called()
        np.testing.assert_array_equal(qa, g.a[1])
        np.testing.assert_array_equal(qb, g.b[1])
        self.assertEqual(status['source'], 'saved_normalized_vectors')
        self.assertEqual(ids, {'b'})

    def test_known_missing_b_reuses_only_a_without_inference(self):
        g = gallery()
        g.missing_b[0]['reason'] = 'hair empty'
        with patch.object(ab, 'identify_query', return_value=({'missing'}, 'sha')), patch.object(ab, 'run_worker') as worker:
            qa, qb, _, status = ab.query_vectors(Path('missing.png'), g, Path('.'))
        worker.assert_not_called()
        self.assertIsNone(qb)
        self.assertEqual(qa[0], 999)
        self.assertEqual(status['reason'], 'hair empty')

    def test_worker_uses_original_environment_and_argument_list(self):
        for kind, env in [('a', '.venv311'), ('b', '.venv-uniface')]:
            with tempfile.TemporaryDirectory() as folder:
                destination = Path(folder)
                ab.write_json(destination / f'{kind}_status.json', {'status': 'valid'})
                with patch.object(ab.Path, 'is_file', return_value=True), patch.object(ab.subprocess, 'run') as run:
                    run.return_value.returncode = 0
                    ab.run_worker(kind, Path('space name.png'), destination)
                command = run.call_args.args[0]
                self.assertIn(env, command[0])
                self.assertIn('space name.png', command)
                self.assertFalse(run.call_args.kwargs.get('shell', False))


if __name__ == '__main__':
    unittest.main()
