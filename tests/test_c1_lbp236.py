"""Numerical and failure-path tests for the provisional C1 technical trial."""
from pathlib import Path
import copy
import json
import math
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from features.C1_lbp.src import lbp236 as target
from features.C1_lbp.verification import scalar_oracle as oracle


class C1NumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = target.Context()
        cls.engine = target.Extractor(cls.context)

    def test_grayscale_known_color_fixture_and_overflow(self):
        bgr = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255], [0, 0, 0],
                         [13, 207, 83], [252, 253, 254]]], np.uint8)
        actual = target.grayscale(bgr)
        np.testing.assert_array_equal(actual[0, :5], [29, 150, 76, 255, 0])
        np.testing.assert_array_equal(actual, oracle.gray_image(bgr))
        self.assertEqual(actual.dtype, np.float64)

    def test_grayscale_random_against_integer_oracle(self):
        bgr = np.random.default_rng(3201).integers(0, 256, (31, 39, 3), dtype=np.uint8)
        np.testing.assert_array_equal(target.grayscale(bgr), oracle.gray_image(bgr))

    def test_constant_and_equality_bit_one(self):
        gray = np.full((9, 9), 73., np.float64)
        np.testing.assert_array_equal(target.neighbours(gray, np.array([4]), np.array([4])), np.full((1, 8), 73.))
        self.assertEqual(int(target.raw_codes(gray, np.array([4]), np.array([4]))[0]), 255)
        self.assertEqual(int(self.context.codebook[255]), 57)

    def test_all_256_codebook_entries_independent_rotations(self):
        expected = oracle.codebook()
        np.testing.assert_array_equal(self.context.codebook, expected)
        self.assertEqual(expected.count(58), 198)
        self.assertEqual(len(set(v for v in expected if v != 58)), 58)
        self.assertEqual(set(expected), set(range(59)))

    def test_orientation_is_preserved(self):
        self.assertEqual([int(self.context.codebook[c]) for c in [0, 1, 2, 3, 129, 170, 255]], [0, 1, 8, 9, 10, 58, 57])

    def test_all_256_known_neighbour_patterns(self):
        # Disjoint stencil sets; construct each possible raw word at (4,4).
        for word in range(256):
            gray = np.full((9, 9), 100., np.float64)
            q = math.sqrt(2.)
            offsets = [(2., 0.), (q, -q), (0., -2.), (-q, -q), (-2., 0.), (-q, q), (0., 2.), (q, q)]
            for p, (dx, dy) in enumerate(offsets):
                for x in {math.floor(4 + dx), math.ceil(4 + dx)}:
                    for y in {math.floor(4 + dy), math.ceil(4 + dy)}:
                        gray[y, x] = 200. if word & (1 << p) else 0.
            actual = int(target.raw_codes(gray, np.array([4]), np.array([4]))[0])
            self.assertEqual(actual, word)
            self.assertEqual(oracle.raw_code(gray, 4, 4), word)

    def test_no_epsilon_in_threshold(self):
        gray = np.full((9, 9), 100., np.float64)
        gray[4, 6] = 100. - 1e-12
        self.assertEqual(int(target.raw_codes(gray, np.array([4]), np.array([4]))[0]), 254)

    def test_sqrt2_bilinear_horizontal_then_vertical(self):
        gray = np.random.default_rng(51).integers(0, 256, (11, 13)).astype(np.float64)
        actual = target.neighbours(gray, np.array([5]), np.array([6]))[0]
        expected = [r['gp'] for r in oracle.neighbours(gray, 6, 5)]
        np.testing.assert_array_equal(actual, expected)
        self.assertNotEqual(float(actual[1]), round(float(actual[1])))
        # Analytic affine plane fixes orientation and sqrt(2), independent of oracle.
        yy, xx = np.indices((11, 13))
        affine = (3 * xx + 7 * yy).astype(np.float64)
        diagonal = target.neighbours(affine, np.array([5]), np.array([6]))[0, 1]
        self.assertAlmostEqual(float(diagonal), 53 - 4 * math.sqrt(2.), places=13)

    def test_support_exactly_21_independent_points(self):
        self.assertEqual(set(target.SUPPORT), set(oracle.support_points()))
        self.assertEqual(len(target.SUPPORT), 21)
        for dx, dy in oracle.support_points():
            mask = np.ones((9, 9), np.uint8)
            mask[4 + dy, 4 + dx] = 0
            self.assertEqual(int(target.eligible_centres(mask)[4, 4]), 0)
        mask = np.ones((9, 9), np.uint8)
        mask[4, 5] = 0  # not in the 21-point footprint
        self.assertEqual(int(target.eligible_centres(mask)[4, 4]), 1)

    def test_no_padding_or_reflection(self):
        with self.assertRaises(ValueError):
            target.raw_codes(np.ones((9, 9)), np.array([0]), np.array([0]))
        support = target.eligible_centres(np.ones((9, 9), np.uint8))
        self.assertEqual(int(support.sum()), 25)
        self.assertFalse(support[:2].any())

    def test_outside_roi_cannot_change_histogram(self):
        mask = np.zeros((32, 32), np.uint8); mask[4:28, 4:28] = 1
        gray = np.random.default_rng(15).integers(0, 256, (32, 32)).astype(np.float64)
        changed = gray.copy(); changed[mask == 0] = 255 - changed[mask == 0]
        for a, b in zip(target.region_histogram(gray, mask, self.context.codebook),
                        target.region_histogram(changed, mask, self.context.codebook)):
            np.testing.assert_array_equal(a, b)

    def test_scalar_histogram_counts_and_l1(self):
        mask = np.zeros((24, 24), np.uint8); mask[2:22, 2:22] = 1
        gray = np.random.default_rng(14).integers(0, 256, (24, 24)).astype(np.float64)
        counts, histogram = target.region_histogram(gray, mask, self.context.codebook)
        expected_counts, expected_hist, selected = oracle.histogram(gray, mask)
        np.testing.assert_array_equal(counts, expected_counts)
        np.testing.assert_array_equal(histogram, expected_hist)
        self.assertEqual(counts.dtype, np.uint64)
        self.assertEqual(int(counts.sum()), len(selected))
        self.assertAlmostEqual(float(histogram.sum()), 1.)

    @staticmethod
    def polygons():
        p = np.array([[20., 20.], [80., 20.], [80., 80.], [20., 80.]])
        return {name: p.copy() for name in target.REGIONS}

    def test_overlap_kept_and_236_float64_four_l1(self):
        result = self.engine._extract_polygons(np.full((256, 256, 3), 75, np.uint8), self.polygons(), 'fixture', 'synthetic')
        self.assertEqual(result['status'], 'valid_C1')
        self.assertEqual(result['vector'].shape, (236,))
        self.assertEqual(result['vector'].dtype, np.float64)
        self.assertEqual(result['vector'].sum(), 4.)
        for name in target.REGIONS:
            self.assertEqual(result['regions'][name]['raw_mask_pixels'], 61 * 61)
            self.assertEqual(result['regions'][name]['eligible_centres'], 57 * 57)
        for row in result['histograms']:
            self.assertEqual(row[57], 1.)
        self.assertTrue(np.all(result['counts'][:, 57] == 57 * 57))

    def test_self_crossing_never_calls_lbp(self):
        polygons = self.polygons()
        polygons[target.REGIONS[0]] = np.array([[20., 20.], [80., 80.], [20., 80.], [80., 20.]])
        with patch.object(target, 'region_histogram', side_effect=AssertionError('LBP forbidden')):
            result = self.engine._extract_polygons(np.zeros((256, 256, 3), np.uint8), polygons, 'bad', 'synthetic')
        self.assertEqual(result['status'], 'missing_C1')
        self.assertIn('self_intersection', result['missing_reason'])
        self.assertIsNone(result['vector']); self.assertIsNone(result['counts'])

    def test_missing_one_region_missing_whole(self):
        polygons = self.polygons(); del polygons[target.REGIONS[-1]]
        result = self.engine._extract_polygons(np.zeros((256, 256, 3), np.uint8), polygons, 'bad', 'synthetic')
        self.assertEqual(result['status'], 'missing_C1'); self.assertIsNone(result['histograms'])

    def test_under64_centres_missing_whole(self):
        polygons = self.polygons(); polygons[target.REGIONS[0]] = np.array([[20., 20.], [27., 20.], [27., 27.], [20., 27.]])
        result = self.engine._extract_polygons(np.zeros((256, 256, 3), np.uint8), polygons, 'bad', 'synthetic')
        self.assertIn('fewer_than_64', result['missing_reason']); self.assertIsNone(result['vector'])

    def test_nonfinite_landmarks_missing(self):
        points = np.ones((478, 2), np.float32); points[0, 0] = np.nan
        result = self.engine.extract(np.zeros((256, 256, 3), np.uint8), points, 'bad', 'synthetic')
        self.assertEqual(result['status'], 'missing_C1')

    def test_query_gallery_locks_and_no_refit(self):
        from features.C1_lbp.src.trial100 import inputs
        images, points = inputs(); identity = 'cfd_final_00001'
        import cv2
        image = cv2.imread(images[identity]['image_path'])
        before = copy.deepcopy(self.context.lock)
        gallery = self.engine.extract(image, points[identity][1], identity, 'cfd')
        query = self.engine.extract(image, points[identity][1], identity, 'cfd', gallery_lock=before)
        np.testing.assert_array_equal(query['vector'], gallery['vector'])
        self.assertEqual(self.context.lock, before)
        self.assertEqual(target.chi_square(query['vector'], gallery['vector']), 0.)
        for key in ('roi_contract_hash', 'lbp_spec_hash', 'codebook_file_sha256'):
            wrong = dict(before); wrong[key] = 'wrong'
            with self.assertRaises(ValueError):
                self.engine.extract(image, points[identity][1], identity, 'cfd', gallery_lock=wrong)

    def test_pin_mismatch_is_fatal(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            for name in ('contract_v0_2.json', 'lbp_implementation_spec.json', 'nri_uniform_59_codebook.csv'):
                (temp / name).write_bytes((target.SPEC_DIR / name).read_bytes())
            changed = json.loads((temp / 'contract_v0_2.json').read_text(encoding='utf-8'))
            changed['polygons']['forehead_brow'][0]['offset_v_ipd'] = .01
            (temp / 'contract_v0_2.json').write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                target.Context(temp)

    def test_chi_square_symmetric_nonnegative_self_and_half(self):
        a = np.zeros((4, 59)); b = np.zeros((4, 59)); a[:, 0] = 1.; b[:, 1] = 1.
        a, b = a.reshape(236), b.reshape(236)
        self.assertEqual(target.chi_square(a, a), 0.)
        self.assertEqual(target.chi_square(a, b), target.chi_square(b, a))
        self.assertAlmostEqual(target.chi_square(a, b), 4. / (1. + 1e-8))
        self.assertGreaterEqual(target.chi_square(a, b), 0.)
        with self.assertRaises(ValueError):
            target.chi_square(a / 4, b)


if __name__ == '__main__':
    unittest.main()
