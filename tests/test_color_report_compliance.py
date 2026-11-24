"""Independent fixtures for report requirements and declared implementation details.

Passing a convention test does not establish that the report specifies it.
No dataset inference, feature persistence, or retrieval output is performed.
"""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from features.B_color.src import color_features as color
from features.B_color.src.batch_uniface import make_masks
from features.B_color.src.run_color_experiment import build_nose_masks, run as run_report_trial
from features.B_color.src.search_color import top5


class ReportFormulaTests(unittest.TestCase):
    def test_hs_bins_l1_and_hue_bins_with_independent_weighted_counts(self):
        # Each HS cell has a different known mass. The conversion is controlled
        # to test bin edges/layout independently of OpenCV color quantization.
        samples = []
        hs_expected = np.zeros(48)
        hue_expected = np.zeros(10)
        for h in range(12):
            for s in range(4):
                count = 4*h+s+1
                hue = 15*h  # exact left edge, including H=0
                saturation = 255 if s == 3 else 64*s
                samples.extend([(hue, saturation, 128)]*count)
                hs_expected[4*h+s] += count
                hue_expected[math.floor(hue/18)] += count
        # Include both last representable endpoints explicitly.
        samples.append((179, 255, 255))
        hs_expected[47] += 1
        hue_expected[9] += 1
        image = np.zeros((len(samples), 1, 3), np.uint8)
        mask = np.full(image.shape[:2], 255, np.uint8)
        hsv = np.asarray(samples, dtype=np.uint8)
        lab = np.zeros((len(samples), 3), np.float32)
        with patch.object(color.cv2, 'cvtColor', side_effect=[hsv, lab]):
            vector, _ = color.region_descriptor(image, mask)
        np.testing.assert_allclose(vector[:48], hs_expected/len(samples), atol=0, rtol=0)
        np.testing.assert_allclose(vector[60:70], hue_expected/len(samples), atol=0, rtol=0)
        self.assertAlmostEqual(math.fsum(vector[:48]), 1)
        self.assertAlmostEqual(math.fsum(vector[60:70]), 1)

    def test_lab_moments_against_closed_form_asymmetric_distribution(self):
        # X={0,0,0,4}: mean=1, variance=3, skew=2/sqrt(3),
        # Pearson kurtosis=7/3 (excess=-2/3). No extractor-derived oracle.
        x = np.repeat(np.array([0, 0, 0, 4], np.float32), 25)
        lab = np.column_stack((20+10*x, x-3, 6-2*x)).astype(np.float32)
        hsv = np.zeros((100, 3), np.uint8)
        image = np.zeros((100, 1, 3), np.uint8)
        mask = np.full((100, 1), 255, np.uint8)
        with patch.object(color.cv2, 'cvtColor', side_effect=[hsv, lab]):
            vector, _ = color.region_descriptor(image, mask)
        expected = [30, 10*math.sqrt(3), 2/math.sqrt(3), 7/3,
                    -2, math.sqrt(3), 2/math.sqrt(3), 7/3,
                    4, 2*math.sqrt(3), -2/math.sqrt(3), 7/3]
        np.testing.assert_allclose(vector[48:60], expected, atol=1e-12, rtol=1e-12)

    def test_144_dimension_region_and_component_order_with_known_colors(self):
        image = np.empty((20, 10, 3), np.uint8)
        image[:10] = (0, 0, 255)  # RGB red via BGR input
        image[10:] = (255, 0, 0)  # RGB blue
        skin = np.zeros((20, 10), np.uint8); skin[:10] = 255
        hair = np.zeros_like(skin); hair[10:] = 255
        before = [a.copy() for a in (image, skin, hair)]
        vector = color.extract_color(image, skin, hair).vector
        self.assertEqual(vector.shape, (144,))
        self.assertTrue(np.isfinite(vector).all())
        expected_hs = np.zeros(96); expected_hs[3] = 1; expected_hs[48+35] = 1
        np.testing.assert_array_equal(np.r_[vector[:48], vector[72:120]], expected_hs)
        expected_hue = np.zeros(20); expected_hue[0] = 1; expected_hue[10+6] = 1
        np.testing.assert_array_equal(np.r_[vector[60:70], vector[132:142]], expected_hue)
        np.testing.assert_allclose(vector[[48, 52, 56]], [53.24, 80.09, 67.20], atol=.3)
        np.testing.assert_allclose(vector[[120, 124, 128]], [32.30, 79.20, -107.86], atol=.3)
        np.testing.assert_allclose(vector[[70, 71, 142, 143]], [0, 0, 2/3, 0], atol=1e-8)
        names = color.feature_names()
        self.assertEqual(len(names), 144)
        expected_names = {0:'skin_HS_h00_s0', 47:'skin_HS_h11_s3',
                          48:'skin_Lab_L_mean', 59:'skin_Lab_b_kurtosis',
                          60:'skin_Hue_bin00', 69:'skin_Hue_bin09',
                          70:'skin_circular_mean', 71:'skin_circular_std',
                          72:'hair_HS_h00_s0', 120:'hair_Lab_L_mean',
                          143:'hair_circular_std'}
        for i, name in expected_names.items():self.assertEqual(names[i], name)
        for actual, original in zip((image, skin, hair), before):
            np.testing.assert_array_equal(actual, original)

    def test_circular_statistics_against_analytic_two_angle_solution(self):
        # Angles 0 and pi/3: resultant=sqrt(3)/2, mean angle=pi/6.
        mean, std, r, warnings = color.hue_statistics([0, 30])
        self.assertAlmostEqual(mean, 1/12, places=14)
        self.assertAlmostEqual(r, math.sqrt(3)/2, places=14)
        self.assertAlmostEqual(std, math.sqrt(math.log(4/3))/(2*math.pi), places=14)
        self.assertFalse(warnings)
        mean, std, r, _ = color.hue_statistics([179, 1])
        self.assertAlmostEqual(mean, 0, places=14)
        self.assertAlmostEqual(r, math.cos(math.pi/90), places=14)
        self.assertAlmostEqual(std, math.sqrt(-2*math.log(math.cos(math.pi/90)))/(2*math.pi), places=14)

    def test_declared_degenerate_conventions_are_flagged(self):
        mean, std, _, warnings = color.hue_statistics([0, 90])
        self.assertEqual((mean, std), (0, 1))
        self.assertIn('circular_mean_undefined_low_resultant', warnings)
        image = np.zeros((10, 10, 3), np.uint8)
        vector, info = color.region_descriptor(image, np.full((10, 10), 255, np.uint8))
        np.testing.assert_array_equal(vector[48:60], np.zeros(12))
        self.assertEqual(sum('zero_variance' in w for w in info['warnings']), 3)

    def test_gallery_zscore_and_unseen_query_against_hand_calculation(self):
        matrix = np.zeros((3, 144))
        matrix[:, 0] = [1, 3, 5]; matrix[:, 1] = [2, 6, 10]; matrix[:, 2] = 7
        stats = color.fit_standardizer(matrix)
        np.testing.assert_array_equal(stats['mean'][:3], [3, 6, 7])
        np.testing.assert_allclose(stats['std'][:3], [math.sqrt(8/3), math.sqrt(32/3), 1])
        expected = np.zeros((3, 144))
        expected[:, 0] = [-math.sqrt(1.5), 0, math.sqrt(1.5)]
        expected[:, 1] = expected[:, 0]
        np.testing.assert_allclose(color.transform(matrix, stats), expected, atol=1e-14)
        query = np.zeros(144); query[:3] = [7, 14, 9]
        original_stats = {k:v.copy() if isinstance(v, np.ndarray) else v for k,v in stats.items()}
        expected_query = np.zeros(144); expected_query[:3] = [math.sqrt(6), math.sqrt(6), 2]
        np.testing.assert_allclose(color.transform(query, stats), expected_query, atol=1e-14)
        for key in ('mean', 'std', 'constant_dimensions'):
            np.testing.assert_array_equal(stats[key], original_stats[key])

    def test_near_zero_variance_policy_does_not_remove_or_refit_dimensions(self):
        matrix = np.zeros((3, 144)); matrix[:, 0] = [-1e-10, 0, 1e-10]
        stats = color.fit_standardizer(matrix)
        self.assertEqual(stats['std'][0], 1)
        self.assertIn(0, stats['constant_dimensions'])
        np.testing.assert_array_equal(color.transform(matrix, stats), matrix)

    def test_report_runner_rejects_moments_only_before_any_output_or_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'must_not_be_created'
            with self.assertRaisesRegex(ValueError, 'section 2.3.3 requires all144'):
                run_report_trial(output, Path(folder)/'not_loaded.pdf', profile='moments_only')
            self.assertFalse(output.exists())

    def test_euclidean_distance_uses_all_coordinates_and_square_root(self):
        matrix = np.zeros((7, 144))
        matrix[1, [0, 143]] = [3, 4]
        matrix[2, [0, 143]] = [-3, -4]
        matrix[3, 71] = 1; matrix[4, [48, 120]] = [6, 8]
        matrix[5, 142] = 12; matrix[6, [0, 143]] = [5, 12]
        result = top5(matrix, ['q','b','a','near','ten','twelve','far'], 'q')
        self.assertEqual([r['image_name'] for r in result], ['near','a','b','ten','twelve'])
        self.assertEqual([r['distance'] for r in result], [1,5,5,10,12])

    def test_class_masks_and_erosion_against_manual_neighborhood_intersection(self):
        labels = np.zeros((256, 256), np.uint8)
        labels[10:15, 10:15] = 1; labels[30:33, 30:33] = 17
        labels[20, 20] = 10; labels[40, 40] = 14
        before = labels.copy(); masks = make_masks(labels)
        expected_skin = np.zeros((256, 256), np.uint8); expected_skin[10:15, 10:15] = 255
        expected_hair = np.zeros_like(expected_skin); expected_hair[30:33, 30:33] = 255
        np.testing.assert_array_equal(masks['skin'], expected_skin)
        np.testing.assert_array_equal(masks['hair'], expected_hair)
        for name, raw in (('skin', expected_skin), ('hair', expected_hair)):
            manual = np.zeros_like(raw)
            for y in range(1, 255):
                for x in range(1, 255):
                    if np.all(raw[y-1:y+2, x-1:x+2] == 255):manual[y, x] = 255
            np.testing.assert_array_equal(masks[name+'_clean'], manual)
        skin_nose, hair = build_nose_masks(np.zeros((256,256,3), np.uint8), labels)
        expected_skin[20,20] = 255
        np.testing.assert_array_equal(skin_nose, expected_skin)
        np.testing.assert_array_equal(hair, expected_hair)
        np.testing.assert_array_equal(labels, before)


if __name__ == '__main__':
    unittest.main()
