"""Version binding, identity/ranking and real full-gallery integration tests."""
from pathlib import Path
import json
import math
import tempfile
import unittest

import numpy as np

from features.C1_lbp.src import lbp236 as kernel
from features.C1_lbp.src.full_v04 import V04Context, ROI_HASH, ROI_PATH, OUT
from retrieval.search_c1 import C1Gallery, rank_vectors


def vector(first=(1., 0., 0.)):
    h = np.zeros((4, 59), np.float64); h[:, 0] = 1.
    h[0, :3] = first
    return h.ravel()


def scalar_chi(a, b):
    return .5 * math.fsum((float(x)-float(y))**2/(float(x)+float(y)+1e-8) for x, y in zip(a, b))


class FullV04UnitTests(unittest.TestCase):
    def test_binding_keeps_original_context_and_arithmetic(self):
        before = kernel.Context(); current = V04Context()
        self.assertEqual(before.lock['roi_contract_hash'], kernel.ROI_HASH)
        self.assertEqual(current.lock['roi_contract_hash'], ROI_HASH)
        self.assertEqual(current.spec, before.spec)
        np.testing.assert_array_equal(current.codebook, before.codebook)
        self.assertFalse(current.roi['active'])
        for name in kernel.REGIONS[1:]: self.assertEqual(current.roi['polygons'][name], before.roi['polygons'][name])

    def test_modified_candidate_rejected(self):
        c = json.loads(ROI_PATH.read_text(encoding='utf-8')); c['polygons']['forehead_brow'][0]['offset_v_ipd'] = .01
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'modified.json'; p.write_text(json.dumps(c), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): V04Context(p)

    def test_independent_chi_half_epsilon_symmetry_and_self(self):
        a, b = vector((.9, .09, .01)), vector((.86, .13, .01))
        self.assertAlmostEqual(kernel.chi_square(a, b), scalar_chi(a, b), places=16)
        self.assertEqual(kernel.chi_square(a, b), kernel.chi_square(b, a))
        self.assertEqual(kernel.chi_square(a, a), 0.)
        c, d = np.zeros((4, 59)), np.zeros((4, 59)); c[:, 0] = 1; d[:, 1] = 1
        self.assertAlmostEqual(kernel.chi_square(c.ravel(), d.ravel()), 4/(1+1e-8))

    def test_chi_ranking_differs_from_Euclid_fixture(self):
        q, a, b = vector((.9,.09,.01)), vector((.86,.13,.01)), vector((.9,.07,.03))
        self.assertGreater(np.linalg.norm(q-a), np.linalg.norm(q-b))
        self.assertLess(scalar_chi(q,a), scalar_chi(q,b))
        result = rank_vectors(np.stack([b,a]), ['B','A'], q)
        self.assertEqual([r[0] for r in result], ['A','B'])

    def test_exclude_ID_not_all_zero_distance_and_tie_break(self):
        q = vector(); matrix = np.stack([q,q,q,vector((0.,1.,0.))])
        ids = ['query','z','a','far']
        before = matrix.copy()
        result = rank_vectors(matrix, ids, q, query_id='query')
        self.assertEqual([r[0] for r in result], ['a','z','far'])
        self.assertEqual(result[0][1], 0.)
        np.testing.assert_array_equal(matrix, before)
        permutation = [3,1,0,2]
        self.assertEqual(result, rank_vectors(matrix[permutation], [ids[i] for i in permutation], q, query_id='query'))

    def test_bad_inputs_and_wrong_epsilon_rejected(self):
        q = vector()
        for options in [dict(top_k=0), dict(epsilon=1e-5)]:
            with self.assertRaises(ValueError): rank_vectors(np.stack([q]), ['a'], q, **options)
        with self.assertRaises(ValueError): rank_vectors(np.stack([q/4]), ['a'], q)
        with self.assertRaises(ValueError): rank_vectors(np.stack([q,q]), ['a','a'], q)

    def test_missing_input_not_zero_filled(self):
        result = kernel.Extractor(V04Context()).extract(np.zeros((256,256,3), np.uint8), None, 'fixture','synthetic')
        self.assertEqual(result['status'], 'missing_C1'); self.assertIsNone(result['vector']); self.assertTrue(result['missing_reason'])


@unittest.skipUnless((OUT / 'manifest.json').exists(), 'Build full_v04 first')
class FullV04IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.g = C1Gallery()

    def test_all_input_statuses_and_valid_shapes(self):
        self.assertEqual(len(self.g.statuses),1438)
        self.assertEqual(len(self.g.rows) + self.g.manifest['missing_images'],1438)
        self.assertEqual(self.g.matrix.shape,(len(self.g.rows),236))
        self.assertEqual(self.g.matrix.dtype,np.float64)
        self.assertTrue(np.isfinite(self.g.matrix).all())
        np.testing.assert_allclose(self.g.matrix.reshape(-1,4,59).sum(axis=2),1.,rtol=0,atol=1e-12)
        for s in self.g.statuses.values():
            if s['status']=='missing_C1': self.assertTrue(s['missing_reason']); self.assertEqual(s['feature_row_index'],'')

    def test_CFD_HF_queries_self_zero_and_exclusion(self):
        for identity in ['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00198','hf_merged_00209']:
            q = self.g.vector(identity)
            self.assertEqual(kernel.chi_square(q,q),0.)
            _, rows = self.g.search(identity+'.png')
            self.assertEqual(len(rows),5); self.assertNotIn(identity,[r['image_id'] for r in rows])
            self.assertEqual([(r['distance_C1'],r['image_id']) for r in rows], sorted((r['distance_C1'],r['image_id']) for r in rows))
            for row in rows: self.assertAlmostEqual(row['distance_C1'],scalar_chi(q,self.g.vector(row['image_id'])),places=14)

    def test_unchanged_three_regions_match_old_trial_all96_vectors(self):
        old = OUT.parent / 'trial100_spec_v0_1'
        m = json.loads((old/'manifest.json').read_text(encoding='utf-8'))['images']
        values = np.load(old/'gallery_vectors.npy',allow_pickle=False)
        count = 0
        for row in m:
            if row['status']!='valid_C1': continue
            np.testing.assert_array_equal(self.g.vector(row['image_id']).reshape(4,59)[1:],values[row['feature_row_index']].reshape(4,59)[1:])
            count += 1
        self.assertEqual(count,96)

    def test_new_image_and_modified_same_name_not_assumed_aligned(self):
        with self.assertRaisesRegex(ValueError,'Gallery query only'): self.g.search('not_a_gallery_image.png')
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'cfd_final_00001.png'; p.write_bytes(b'not same gallery data')
            with self.assertRaisesRegex(ValueError,'differs from'): self.g.search(p)


if __name__ == '__main__': unittest.main()
