"""Checks generated evidence and negative review cases; no feature calls."""
from pathlib import Path
from collections import Counter
import copy
import io
import json
import unittest

import cv2
import numpy as np

import build_review as bundle
import validate_review as review


class ReviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = bundle.source.read_json(bundle.OUT / 'review_manifest.json')
        cls.rows = bundle.source.read_csv(bundle.OUT / 'review_annotations.csv')

    def test_initial_records_are_all_NOT_REVIEWED(self):
        result = review.validate(self.rows, self.manifest)
        self.assertEqual(result['anatomy_status_counts']['NOT_REVIEWED'], 800)
        self.assertEqual(result['human_review_rows'], 0)
        self.assertTrue(all(not r['reviewer'] and not r['review_date'] for r in self.rows))

    def test_geometry_does_not_create_anatomy_acceptance(self):
        self.assertEqual(sum(r['geometry_status'] != 'GEOMETRY_VALID' for r in self.rows), 4)
        self.assertEqual({r['anatomy_review_status'] for r in self.rows}, {'NOT_REVIEWED'})

    def test_unauthorized_ACCEPT_is_rejected(self):
        rows = copy.deepcopy(self.rows); rows[0]['anatomy_review_status'] = 'ACCEPT'
        with self.assertRaisesRegex(ValueError, 'Human reviewer'): review.validate(rows, self.manifest)

    def test_named_agent_is_not_authority(self):
        rows = copy.deepcopy(self.rows); row = rows[0]
        row.update(anatomy_review_status='UNCERTAIN', reviewer='SYNTHETIC_AGENT_NOT_HUMAN_REVIEWER',
                   review_date='2026-11-24', occlusion_observation='Synthetic test only', reason='Synthetic test only',
                   left_right_reference='UNCERTAIN', **{q: 'UNCERTAIN' for q in bundle.QUESTIONS})
        with self.assertRaisesRegex(ValueError, 'lacks recorded'): review.validate(rows, self.manifest)

    def test_review_date_requires_YYYY_MM_DD(self):
        rows = copy.deepcopy(self.rows)
        rows[0].update(anatomy_review_status='UNCERTAIN', reviewer='SYNTHETIC_TEST_ONLY', review_date='20261124')
        with self.assertRaisesRegex(ValueError, 'ISO YYYY-MM-DD'): review.validate(rows, self.manifest)

    def test_invalid_status_rejected(self):
        rows = copy.deepcopy(self.rows); rows[0]['anatomy_review_status'] = 'GEOMETRY_VALIDATED'
        with self.assertRaisesRegex(ValueError, 'Invalid anatomy'): review.validate(rows, self.manifest)

    def test_hash_changes_rejected(self):
        rows = copy.deepcopy(self.rows); rows[0]['contract_content_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'Immutable'): review.validate(rows, self.manifest)

    def test_missing_or_duplicate_case_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exactly800'): review.validate(self.rows[1:], self.manifest)
        rows = copy.deepcopy(self.rows); rows[-1] = rows[0]
        with self.assertRaisesRegex(ValueError, 'duplicate'): review.validate(rows, self.manifest)

    def test_reproducible_balanced_selection(self):
        metrics = bundle.source.read_csv(bundle.source.OUT / 'roi_metrics.csv')
        a, mandatory, extrema = bundle.select_images(metrics); b, _, _ = bundle.select_images(metrics)
        self.assertEqual(a, b)
        self.assertEqual([x[0] for x in a], self.manifest['selected_ids'])
        self.assertTrue(set(mandatory).issubset(self.manifest['selected_ids']))
        self.assertEqual(self.manifest['source_counts'], {'cfd': 50, 'hf': 50})
        self.assertTrue(all(r['image_id'] in self.manifest['selected_ids'] for r in extrema))


def main():
    target = bundle.OUT / 'verification.json'
    if target.exists(): raise FileExistsError('Verification complete; no overwrite')
    manifest = bundle.source.read_json(bundle.OUT / 'review_manifest.json')
    assert len(manifest['images']) == len(set(manifest['selected_ids'])) == 100
    pair = bundle.contracts()
    original_metrics = bundle.source.read_csv(bundle.source.OUT / 'roi_metrics.csv')
    metrics = {(r['variant'], r['image_id'], r['region']): r for r in original_metrics}
    mask_count, diff_count = 0, 0
    for record in manifest['images']:
        identity = record['image_id']; folder = bundle.OUT / 'contact_sheets' / identity
        assert bundle.source.digest(folder / 'original.png') == record['image_sha256']
        contact = cv2.imread(str(folder / 'contact.png'))
        assert contact is not None and contact.shape == (1278, 1536, 3)
        assert cv2.imread(str(folder / 'landmarks.png')).shape == (960, 1536, 3)
        for version, short, tag in [(bundle.V02, 'v02', 'v0_2'), (bundle.V04, 'v04', 'candidate_v0_4')]:
            for region in bundle.REGIONS:
                mask = cv2.imread(str(folder / (short + '_' + region + '_raw.png')), cv2.IMREAD_GRAYSCALE)
                assert set(np.unique(mask)).issubset({0, 255})
                raw = (mask != 0).astype(np.uint8)
                assert bundle.source.hashlib.sha256(raw.tobytes()).hexdigest() == metrics[(tag, identity, region)]['raw_mask_sha256']
                assert int(raw.sum()) == record['measurements'][version][region]['raw_mask_pixels']
                mask_count += 1
        for region in bundle.REGIONS:
            old = cv2.imread(str(folder / ('v02_' + region + '_raw.png')), 0) != 0
            new = cv2.imread(str(folder / ('v04_' + region + '_raw.png')), 0) != 0
            added = cv2.imread(str(folder / (region + '_added.png')), 0) != 0
            removed = cv2.imread(str(folder / (region + '_removed.png')), 0) != 0
            np.testing.assert_array_equal(added, new & ~old)
            np.testing.assert_array_equal(removed, old & ~new)
            diff_count += 2
            if region != 'forehead_brow': np.testing.assert_array_equal(old, new)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReviewContractTests))
    print(output.getvalue(), end='', flush=True)
    with (bundle.OUT / 'tests.log').open('x', encoding='utf-8') as stream: stream.write(output.getvalue())
    if not result.wasSuccessful(): raise AssertionError('Review tests failed')
    baseline = bundle.check_baseline()
    assert not list(bundle.OUT.rglob('*.npy')) and not list(bundle.OUT.rglob('*.npz'))
    bundle.source.write_json(target, dict(schema_id='C1_V04_REVIEW_PACKAGE_VERIFICATION_v1', status='PASS',
        image_count=100, annotation_rows=800, all_anatomy_rows_NOT_REVIEWED=True, human_reviews_recorded=0,
        tests_run=result.testsRun, test_failures=len(result.failures), test_errors=len(result.errors),
        raw_mask_round_trips=mask_count, binary_difference_checks=diff_count, original_image_hash_checks=100,
        immutable_previous_files=len(baseline), changed_previous_files=[],
        candidate_activated=False, new_C1C2_vectors=0, LBP_HOG_calls=0, retrieval_rankings=0,
        approval_status='NO_HUMAN_APPROVAL_RECORDED'))
    print('PASS:', mask_count, 'raw masks;', diff_count, 'pixel-change checks;', len(baseline), 'old files unchanged', flush=True)


if __name__ == '__main__': main()
