"""Independent numerical and version-boundary oracles for report v2."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import math

import numpy as np

from features.A_geometry.src import report_v2 as a
from features.B_color.src import report_v2 as b
from retrieval import search_ab_v2 as ab
from retrieval import search_ab as original_ab
from shared.report_v2 import save_csv, read_json, write_json, pair_ids_digest, fresh_output


class AReportV2Tests(unittest.TestCase):
    def test_normal_sigma_and_gallery_transform(self):
        x = np.tile(np.array([1., 3., 5.])[:, None], (1, 150))
        stats = a.fit(x)
        sigma = math.sqrt(8 / 3)
        self.assertEqual(stats['mean'][0], 3)
        self.assertAlmostEqual(stats['raw_sigma'][0], sigma)
        self.assertEqual(stats['effective_divisor'][0], sigma + 1e-8)
        np.testing.assert_allclose(a.transform(x, stats)[:, 0], [-2 / (sigma + 1e-8), 0, 2 / (sigma + 1e-8)], rtol=0, atol=1e-15)

    def test_zero_sigma_retains_all_150_dimensions_and_query_not_forced_zero(self):
        x = np.full((3, 150), 7.)
        stats = a.fit(x)
        np.testing.assert_array_equal(stats['effective_divisor'], np.full(150, 1e-8))
        np.testing.assert_array_equal(a.transform(x, stats), np.zeros((3, 150)))
        np.testing.assert_array_equal(a.transform(np.full(150, 9.), stats), np.full(150, 2e8))

    def test_tiny_sigma_does_not_fall_back_to_one(self):
        x = np.tile(np.array([1e-10, 3e-10, 5e-10])[:, None], (1, 150))
        stats = a.fit(x)
        divisor = math.sqrt(8 / 3) * 1e-10 + 1e-8
        self.assertAlmostEqual(stats['effective_divisor'][0], divisor, delta=1e-23)
        self.assertNotEqual(stats['effective_divisor'][0], 1.)
        self.assertAlmostEqual(a.transform(np.zeros(150), stats)[0], -3e-10 / divisor)

    def test_query_reuses_saved_stats_and_never_refits(self):
        stats = a.fit(np.tile(np.array([1., 3., 5.])[:, None], (1, 150)))
        with patch.object(a, 'fit', side_effect=AssertionError('Query must not fit')):
            value = a.transform(np.full(150, 11.), stats)
        np.testing.assert_allclose(value, np.full(150, 8 / (math.sqrt(8 / 3) + 1e-8)))

    def test_legacy_b_and_inconsistent_a_stats_are_rejected(self):
        for stats in [dict(mean=np.zeros(150), std=np.ones(150)), b.fit_stage(np.ones((3, 144)), 'final144')]:
            with self.assertRaises(ValueError):
                a.transform(np.zeros(150), stats)
        stats = a.fit(np.ones((3, 150)))
        stats['effective_divisor'] = np.ones(150)
        with self.assertRaises(ValueError):
            a.transform(np.zeros(150), stats)

    def test_nonfinite_and_wrong_shape_rejected_without_mutation(self):
        raw = np.arange(450, dtype=np.float64).reshape(3, 150)
        before = raw.copy()
        a.transform(raw, a.fit(raw))
        np.testing.assert_array_equal(raw, before)
        for invalid in [np.zeros((3, 149)), np.full((3, 150), np.inf)]:
            with self.assertRaises(ValueError):
                a.fit(invalid)


class BReportV2Tests(unittest.TestCase):
    def fixture(self):
        skin = np.zeros((3, 72)); hair = np.zeros((3, 72))
        skin[:, :48] = np.arange(48)[None, :] / sum(range(48))
        hair[:, :48] = skin[:, :48]
        skin[:, 60:70] = .1; hair[:, 60:70] = .1
        skin[:, 48:60] = np.array([1., 3., 5.])[:, None]
        hair[:, 48:60] = np.array([2., 6., 10.])[:, None]
        return skin, hair

    def test_moment_stage_normalizes_24_before_concat(self):
        skin, hair = self.fixture()
        after, z, ms, fs = b.fit_pipeline(skin, hair)
        expected = np.array([-math.sqrt(1.5), 0, math.sqrt(1.5)])
        np.testing.assert_allclose(after[:, b.MOMENT_INDICES], np.tile(expected[:, None], (1, 24)), rtol=0, atol=3e-16)
        np.testing.assert_allclose(ms['mean'], [3.] * 12 + [6.] * 12)
        np.testing.assert_allclose(ms['raw_sigma'], [math.sqrt(8 / 3)] * 12 + [math.sqrt(32 / 3)] * 12)
        np.testing.assert_allclose(fs['mean'][b.MOMENT_INDICES], 0, atol=1e-15)
        np.testing.assert_allclose(fs['raw_sigma'][b.MOMENT_INDICES], 1, atol=1e-15)

    def test_region_inputs_remain_separate_and_unchanged_until_lab_stage(self):
        skin, hair = self.fixture()
        before_skin, before_hair = skin.copy(), hair.copy()
        ms = b.fit_stage(np.concatenate((skin[:, 48:60], hair[:, 48:60]), axis=1), 'moments24')
        s, h = b.normalize_moments_before_concat(skin, hair, ms)
        self.assertEqual(s.shape, (3, 72)); self.assertEqual(h.shape, (3, 72))
        np.testing.assert_array_equal(skin, before_skin); np.testing.assert_array_equal(hair, before_hair)
        np.testing.assert_array_equal(s[:, :48], skin[:, :48]); np.testing.assert_array_equal(s[:, 60:], skin[:, 60:])
        np.testing.assert_array_equal(h[:, :48], hair[:, :48]); np.testing.assert_array_equal(h[:, 60:], hair[:, 60:])

    def test_final_stage_is_fitted_on_post_moment_data_not_raw(self):
        skin, hair = self.fixture()
        after, z, ms, fs = b.fit_pipeline(skin, hair)
        self.assertAlmostEqual(fs['raw_sigma'][48], 1)
        self.assertNotEqual(fs['raw_sigma'][48], ms['raw_sigma'][0])
        np.testing.assert_array_equal(z, (after - fs['mean']) / fs['effective_divisor'])

    def test_b_zero_and_tiny_sigma_keep_d15_divisor_not_a_epsilon(self):
        x = np.tile(np.array([1e-10, 3e-10, 5e-10])[:, None], (1, 24)); x[:, 1] = 7
        stats = b.fit_stage(x, 'moments24')
        self.assertEqual(stats['effective_divisor'][0], 1)
        self.assertEqual(stats['effective_divisor'][1], 1)
        query = np.full(24, 3e-10); query[1] = 9
        value = b.apply_stage(query, stats, 'moments24')
        self.assertEqual(value[1], 2)
        self.assertNotEqual(value[1], 2e8)

    def test_query_uses_both_saved_stages_without_fit(self):
        skin, hair = self.fixture()
        _, _, ms, fs = b.fit_pipeline(skin, hair)
        qs, qh = skin[0].copy(), hair[0].copy()
        qs[48:60] = 7; qh[48:60] = 14
        expected = math.sqrt(6.)
        with patch.object(b, 'fit_stage', side_effect=AssertionError('Query must not fit')):
            value = b.transform_regions(qs, qh, ms, fs)
        np.testing.assert_allclose(value[b.MOMENT_INDICES], np.full(24, expected), atol=1e-15)

    def test_wrong_version_stage_or_a_divisor_is_rejected(self):
        skin, hair = self.fixture()
        _, _, ms, fs = b.fit_pipeline(skin, hair)
        with self.assertRaises(ValueError):
            b.transform_regions(skin[0], hair[0], fs, ms)
        with self.assertRaises(ValueError):
            b.apply_stage(np.zeros(144), a.fit(np.ones((3, 150))), 'final144')
        bad = deepcopy(fs); bad['effective_divisor'] = bad['raw_sigma'] + 1e-8
        with self.assertRaises(ValueError):
            b.apply_stage(np.zeros(144), bad, 'final144')
        with self.assertRaises(ValueError):
            b.apply_stage(np.zeros(144), dict(mean=np.zeros(144), std=np.ones(144)), 'final144')

    def test_raw_descriptor_and_missing_region_policy_unchanged(self):
        image = np.zeros((16, 16, 3), np.uint8); image[:8] = 255
        skin_mask = np.zeros((16, 16), np.uint8); skin_mask[:8] = 255
        skin, hair, status = b.describe_regions(image, skin_mask, 255 - skin_mask)
        self.assertEqual(status['status'], 'valid')
        self.assertEqual(skin[48], 100); self.assertEqual(hair[48], 0)
        self.assertEqual(skin.shape, (72,)); self.assertEqual(hair.shape, (72,))
        _, missing, status = b.describe_regions(image, skin_mask, np.zeros_like(skin_mask))
        self.assertIsNone(missing); self.assertEqual(status['status'], 'missing_B')

    def test_only_two_production_stages_and_matching_shapes_allowed(self):
        with self.assertRaises(ValueError):
            b.fit_stage(np.ones((3, 144)), 'moments_only')
        with self.assertRaises(ValueError):
            b.fit_pipeline(np.ones((3, 72)), np.ones((2, 72)))


class CalibrationV2Tests(unittest.TestCase):
    def fixture(self):
        ar = [dict(image_name=n + '.png', image_path=n + '.png') for n in ('a', 'missing', 'b', 'c')]
        av = np.zeros((4, 150)); av[:, 0] = [0, 999, 3, 6]
        br = [dict(image_id=n, image_name=n + '.png', feature_row_index=bi, a_row_index=ai, status='valid')
              for n, ai, bi in [('c', 3, 0), ('a', 0, 2), ('b', 2, 1)]]
        bv = np.zeros((3, 144)); bv[:, 0] = [8, 4, 0]
        return original_ab.join_galleries(ar, av, br, bv)

    def pairs(self, folder):
        path = folder / 'old_pairs.csv'
        save_csv(path, [dict(image_id_1='a', image_id_2='c', distance_a=99999, distance_b=88888),
                        dict(image_id_1='a', image_id_2='b', distance_a=99999, distance_b=88888),
                        dict(image_id_1='b', image_id_2='c', distance_a=99999, distance_b=88888)])
        return path

    def test_same_ordered_pair_ids_but_recomputed_distances_and_medians(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); source = self.pairs(folder)
            params, reused = ab.calibrate(self.fixture(), folder / 'v2', source)
            self.assertFalse(reused)
            self.assertEqual(params['median_a'], 3); self.assertEqual(params['median_b'], 4)
            self.assertEqual(params['pair_ids_sha256'], pair_ids_digest([('a', 'c'), ('a', 'b'), ('b', 'c')]))
            self.assertEqual(params['feature_versions'], ab.VERSIONS)
            _, reused = ab.calibrate(self.fixture(), folder / 'v2', source)
            self.assertTrue(reused)

    def test_legacy_calibration_and_stale_v2_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); source = self.pairs(folder)
            target = folder / 'v2'; target.mkdir()
            write_json(target / 'median_params.json', dict(median_a=3, median_b=4, epsilon=1e-8))
            with self.assertRaisesRegex(ValueError, 'Wrong-version'):
                ab.calibrate(self.fixture(), target, source)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); source = self.pairs(folder)
            ab.calibrate(self.fixture(), folder / 'v2', source)
            g = self.fixture(); g.fingerprint = {'changed': 'new-vector-hash'}
            with self.assertRaisesRegex(ValueError, 'stale'):
                ab.calibrate(g, folder / 'v2', source)

    def test_calibration_rejects_modified_median_and_invalid_pair_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); source = self.pairs(folder)
            ab.calibrate(self.fixture(), folder / 'v2', source)
            path = folder / 'v2/median_params.json'; value = read_json(path)
            value['median_a'] = 100; write_json(path, value)
            with self.assertRaisesRegex(ValueError, 'median'):
                ab.calibrate(self.fixture(), folder / 'v2', source)
            save_csv(source, [dict(image_id_1='a', image_id_2='missing')])
            with self.assertRaisesRegex(ValueError, 'pair IDs'):
                ab.calibrate(self.fixture(), folder / 'another', source)

    def test_euclidean_median_fusion_and_missing_query_on_same_candidates(self):
        g = self.fixture(); qa = np.zeros(150); qb = np.zeros(144); qa[1] = 4; qb[1] = 3
        result = original_ab.rankings(g, qa, qb, dict(median_a=2, median_b=4, epsilon=.5), .5, .5)
        row = next(r for r in result['ab'] if r['image_id'] == 'b')
        self.assertEqual(row['distance_a'], 5); self.assertEqual(row['distance_b'], 5)
        self.assertAlmostEqual(row['distance_total'], .5 * 5 / 2.5 + .5 * 5 / 4.5)
        missing = original_ab.rankings(g, qa, None, dict(median_a=2, median_b=4, epsilon=.5))
        self.assertEqual(missing['ab'], []); self.assertEqual(missing['b_only'], [])
        self.assertTrue(all(r['distance_b'] is None for r in missing['a_only']))

    def test_output_guard_never_reuses_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            fresh_output(folder / 'v2', folder, 'v2')
            with self.assertRaises(FileExistsError):
                fresh_output(folder / 'v2', folder, 'v2')
            with self.assertRaises(ValueError):
                fresh_output(folder / 'v1', folder, 'v2')


if __name__ == '__main__':
    unittest.main()
