"""C2 identity, Euclidean retrieval, crop and trial/full integrity tests."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from features.C2_hog.src import root_hog as hog
from features.C2_hog.src.common import BASE,read_json,identities,write_json
from retrieval.search_c2 import C2Gallery,rank_vectors


class C2RankingTests(unittest.TestCase):
    def test_identity_permutation_and_duplicates(self):
        rows=[dict(image_id=x) for x in ['z','a','b']]
        self.assertEqual(identities(rows),identities(rows[::-1]))
        with self.assertRaises(ValueError):identities(rows+[rows[0]])

    def test_self_ID_exclusion_and_tie_break(self):
        q=np.zeros(324);q[0]=1;b=np.zeros(324);b[1]=1
        matrix=np.stack([q,q,q,b]);ids=['query','z','a','far'];before=matrix.copy()
        result=rank_vectors(matrix,ids,q,'query')
        self.assertEqual([r[0] for r in result],['a','z','far']);self.assertEqual(result[0][1],0.)
        order=[3,2,0,1];self.assertEqual(result,rank_vectors(matrix[order],[ids[i] for i in order],q,'query'))
        np.testing.assert_array_equal(matrix,before)

    def test_bad_gallery_and_topk(self):
        q=np.zeros(324);q[0]=1
        with self.assertRaises(ValueError):rank_vectors(np.stack([q]),['a'],q,top_k=0)
        with self.assertRaises(ValueError):rank_vectors(np.stack([q/2]),['a'],q)

    def test_outside_crop_cannot_change_C2(self):
        image=np.random.default_rng(34).integers(0,256,(256,256,3),np.uint8);changed=image.copy()
        mask=np.ones((256,256),bool);mask[32:224,48:208]=False;changed[mask]=255-changed[mask]
        np.testing.assert_array_equal(hog.extract_c2(image)['vector'],hog.extract_c2(changed)['vector'])


@unittest.skipUnless((BASE/'full_v1/manifest.json').exists(),'Run gated full C2 batch first')
class C2GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=C2Gallery()

    def test_all1438_status_shape_and_norm(self):
        self.assertEqual(len(self.g.status),1438);self.assertEqual(len(self.g.rows)+self.g.manifest['missing'],1438)
        self.assertEqual(self.g.matrix.shape,(len(self.g.rows),324));self.assertEqual(self.g.matrix.dtype,np.float64)
        np.testing.assert_allclose(np.linalg.norm(self.g.matrix,axis=1),1.,rtol=0,atol=1e-12)
        for row in self.g.status.values():
            if row['status']=='missing_C2':self.assertTrue(row['missing_reason']);self.assertEqual(row['feature_row_index'],'')

    def test_trial_vectors_match_by_identity(self):
        trial=C2Gallery(BASE/'trial100')
        for row in trial.rows:np.testing.assert_array_equal(trial.vector(row['image_id']),self.g.vector(row['image_id']))

    def test_CFD_HF_queries_and_no_assumed_alignment(self):
        for identity in ['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00209']:
            _,rows=self.g.search(identity+'.png');self.assertEqual(len(rows),5);self.assertNotIn(identity,[r['image_id'] for r in rows])
            q=self.g.vector(identity);self.assertEqual(hog.euclidean(q,q),0.)
            for row in rows:self.assertAlmostEqual(row['distance'],hog.euclidean(q,self.g.vector(row['image_id'])),places=15)
        with self.assertRaisesRegex(ValueError,'Gallery query only'):self.g.search('unknown.png')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'cfd_final_00001.png';p.write_bytes(b'not aligned gallery image')
            with self.assertRaisesRegex(ValueError,'differs'):self.g.search(p)

    def test_wrong_query_gallery_spec_rejected(self):
        manifest=read_json(BASE/'full_v1/manifest.json');manifest['spec_hash']='not_this_spec'
        with tempfile.TemporaryDirectory() as folder:
            write_json(Path(folder)/'manifest.json',manifest)
            with self.assertRaisesRegex(ValueError,'lock mismatch'):C2Gallery(folder)


if __name__=='__main__':unittest.main()
