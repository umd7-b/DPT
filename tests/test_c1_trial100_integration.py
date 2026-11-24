"""Integration with actual trial artifacts; skip explicitly if not built."""
from pathlib import Path
import json
import tempfile
import unittest

import cv2
import numpy as np

from features.C1_lbp.src.gallery import TrialGallery
from features.C1_lbp.src import lbp236 as target
from features.C1_lbp.src.trial100 import OUT, inputs, read_csv


@unittest.skipUnless((OUT / 'summary.json').exists(), 'Run the exact100 technical trial first')
class TrialIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gallery = TrialGallery(OUT)
        cls.images, cls.landmarks = inputs()
        cls.manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))['images']

    def test_exact_manifest_membership_and_order(self):
        plan = json.loads((target.SPEC_DIR / 'trial100_manifest.json').read_text(encoding='utf-8'))['images']
        self.assertEqual([(r['image_id'], r['source']) for r in self.manifest], [(r['image_id'], r['source']) for r in plan])
        self.assertEqual(len(self.manifest), 100)
        self.assertEqual(len(self.gallery.rows), 96)

    def test_actual_negative_images_no_feature_rows(self):
        missing = {r['image_id']: r for r in self.manifest if r['status'] == 'missing_C1'}
        self.assertEqual(set(missing), {'hf_merged_00069', 'hf_merged_00198', 'hf_merged_00267', 'hf_merged_00463'})
        for identity, row in missing.items():
            self.assertEqual(row['missing_reason'], 'forehead_brow:self_intersection')
            self.assertIsNone(row['feature_row_index'])
            with self.assertRaises(KeyError):
                self.gallery.vector(identity)
            result = self.gallery.extract_query(cv2.imread(self.images[identity]['image_path']), self.landmarks[identity][1], identity, 'hf')
            self.assertIsNone(result['vector']); self.assertIsNone(result['histograms'])

    def test_actual_query_gallery_bitwise_and_identity_join(self):
        for identity in ('cfd_final_00001', 'hf_merged_00209', 'hf_merged_00722'):
            result = self.gallery.extract_query(cv2.imread(self.images[identity]['image_path']), self.landmarks[identity][1], identity, 'test')
            np.testing.assert_array_equal(result['vector'], self.gallery.vector(identity))
        self.assertEqual(self.gallery.vector('hf_merged_00209').shape, (236,))

    def test_all400_masks_match_frozen_census(self):
        frozen = {(r['image_id'], r['region']): r for r in read_csv(target.SPEC_DIR / 'metrics.csv')}
        for row in self.manifest:
            record = json.loads((OUT / 'images' / (row['image_id'] + '.json')).read_text(encoding='utf-8'))
            for name in target.REGIONS:
                expected = frozen[(row['image_id'], name)]
                self.assertEqual(record['regions'][name]['raw_mask_sha256'], expected['raw_mask_sha256'])
                self.assertEqual(record['regions'][name]['eligible_centres'], int(expected['support_valid_centres']))

    def test_gallery_rejects_wrong_hash_and_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            for name in ('contract_lock.json', 'manifest.json', 'gallery_vectors.npy'):
                (temp / name).write_bytes((OUT / name).read_bytes())
            lock = json.loads((temp / 'contract_lock.json').read_text(encoding='utf-8'))
            lock['lbp_spec_hash'] = 'changed'
            (temp / 'contract_lock.json').write_text(json.dumps(lock), encoding='utf-8')
            with self.assertRaises(ValueError):
                TrialGallery(temp)
            (temp / 'contract_lock.json').write_bytes((OUT / 'contract_lock.json').read_bytes())
            manifest = json.loads((temp / 'manifest.json').read_text(encoding='utf-8'))
            manifest['images'][1]['image_id'] = manifest['images'][0]['image_id']
            (temp / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                TrialGallery(temp)

    def test_three_known_dataset_violations_are_retained(self):
        catalog = {r['image_id']: r for r in self.manifest}
        for identity in ('hf_merged_00333', 'hf_merged_00561', 'hf_merged_00722'):
            self.assertEqual(catalog[identity]['dataset_status'], 'KNOWN_VIOLATION')
            self.assertEqual(catalog[identity]['status'], 'valid_C1')
            self.assertEqual(catalog[identity]['ROI_ANATOMY_STATUS'], 'PROVISIONAL')


if __name__ == '__main__':
    unittest.main()
