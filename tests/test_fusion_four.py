"""Fusion arithmetic, identity, frozen input guards and real gallery integration."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from retrieval import fusion_four as f
from retrieval import search_fusion as search
from retrieval import fusion_oracle as oracle
from shared.report_v2 import write_json,digest,read_json


class FusionMathTests(unittest.TestCase):
    def test_all_four_distances_and_chi_coefficient(self):
        x={k:np.zeros(n) for k,n in f.DIMENSIONS.items()}
        y={k:np.ones(n) for k,n in f.DIMENSIONS.items()}
        raw=f.component_distances(x,y)
        for k,n in f.DIMENSIONS.items():
            expected=oracle.chi_square(x[k],y[k]) if k=='c1' else oracle.euclidean(x[k],y[k])
            self.assertAlmostEqual(raw[k],expected,places=12)
        self.assertAlmostEqual(raw['c1'],118/(1+1e-8),places=12)

    def test_self_distance_zero_each_component(self):
        rng=np.random.default_rng(61)
        q={k:rng.random(n) for k,n in f.DIMENSIONS.items()}
        self.assertTrue(all(x==0 for x in f.component_distances(q,q).values()))

    def test_normalization_epsilon_and_unequal_weights(self):
        raw=dict(a=np.array([2.,4.]),b=np.array([3.,2.]),c1=np.array([.3,.1]),c2=np.array([.2,.5]))
        medians=dict(a=2.,b=3.,c1=.3,c2=.2);weights=(.1,.2,.3,.4)
        norm,total=f.combine(raw,{'medians':medians},weights)
        for i in range(2):
            expected=oracle.fusion({k:raw[k][i] for k in f.KINDS},medians,weights)
            self.assertAlmostEqual(total[i],expected,places=15)
        self.assertEqual(norm['a'][0],2/(2+1e-8))

    def test_invalid_weights_refused(self):
        for weights in [(1,1,1,1),(-.1,.1,.5,.5),(np.nan,.25,.25,.25),
                        (np.inf,0,0,0),(.5,.5),(0,0,0,0),(.25,.25,.25,.250000001)]:
            with self.subTest(weights=weights),self.assertRaises(ValueError):f.validate_weights(weights)

    def test_valid_boundary_weights_and_no_renormalization(self):
        np.testing.assert_array_equal(f.validate_weights((1,0,0,0)),[1,0,0,0])
        weights=(.25,.25,.25,.25+5e-13)
        np.testing.assert_array_equal(f.validate_weights(weights),weights)

    def test_self_exclusion_and_tie_break_by_id(self):
        ids=['query','z','a','far'];scores=np.array([0.,0.,0.,1.])
        self.assertEqual([ids[i] for i in f.rank_indices(ids,scores,'query',9)],['a','z','far'])
        with self.assertRaises(ValueError):f.rank_indices(ids,scores,'query',0)

    def test_distance_nonfinite_rejected(self):
        x={k:np.ones(n) for k,n in f.DIMENSIONS.items()};x['a'][0]=np.nan
        with self.assertRaises(ValueError):f.component_distances(x,x)

    def fixtures(self):
        sources={}
        for kind,n in f.DIMENSIONS.items():
            ids=['a','missing','z'] if kind!='b' else ['a','z']
            field='a_row_index' if kind=='a' else 'feature_row_index'
            rows=[dict(image_id=key,**{field:i}) for i,key in enumerate(ids)]
            matrix=np.array([np.full(n,{'a':11.,'missing':22.,'z':33.}[key]) for key in ids])
            sources[kind]=(rows,matrix)
        return sources

    def test_join_permuted_metadata_missing_middle_B(self):
        sources=self.fixtures();ids,joined,_=f.join_by_id(sources)
        self.assertEqual(ids,['a','z'])
        for kind in f.KINDS:
            sources[kind]=(sources[kind][0][::-1],sources[kind][1])
        ids2,joined2,_=f.join_by_id(sources)
        self.assertEqual(ids,ids2)
        for kind in f.KINDS:
            np.testing.assert_array_equal(joined[kind],joined2[kind])
            self.assertEqual(joined2[kind][1,0],33.)

    def test_duplicate_id_or_index_rejected(self):
        for field,value in [('image_id','a'),('a_row_index',0),('a_row_index',99)]:
            sources=self.fixtures();sources['a'][0][1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):f.join_by_id(sources)

    def test_bad_dtype_shape_and_nan_rejected(self):
        for transform in [lambda x:x.astype(np.float32),lambda x:x[:,:-1],lambda x:np.full_like(x,np.inf)]:
            sources=self.fixtures();rows,m=sources['a'];sources['a']=(rows,transform(m))
            with self.assertRaises(ValueError):f.join_by_id(sources)

    def test_input_hash_guard_and_policy_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'input';p.write_bytes(b'original');expected=digest(p)
            f.verify_inputs({str(p):expected});p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):f.verify_inputs({str(p):expected})
            with patch.object(f,'POLICY_PATH',p),self.assertRaisesRegex(ValueError,'policy hash'):f.policy()


class FusionGalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=f.FourGallery();cls.params=f.load_calibration(cls.g)

    def test_counts_versions_and_real_ID_alignment(self):
        self.assertEqual(len(self.g.ids),1437)
        for kind in f.KINDS:
            self.assertEqual(self.g.vectors[kind].shape,(1437,f.DIMENSIONS[kind]))
            rows,matrix=self.g.sources[kind]
            for i,key in enumerate(self.g.ids):
                np.testing.assert_array_equal(self.g.vectors[kind][i],matrix[self.g.maps[kind][key][0]])
        self.assertNotIn('hf_merged_00209',self.g.ids)

    def test_same_candidate_pool_and_exclude_self_all_modes(self):
        for key in ['cfd_final_00001','hf_merged_00001']:
            r=search.search(self.g,self.params,key,2000)
            self.assertEqual(r['candidate_count'],1436);self.assertEqual(r['self_exclusion_count'],1)
            expected=set(self.g.ids)-{key}
            for rows in r['modes'].values():self.assertEqual({x['image_id'] for x in rows},expected)

    def test_missing_B_truthful_no_results_or_redistribution(self):
        r=search.search(self.g,self.params,'hf_merged_00209.png')
        self.assertEqual(r['status'],'fusion_unavailable');self.assertEqual(r['missing_feature'],'missing_B')
        self.assertEqual(r['available_features'],['a','c1','c2'])
        self.assertEqual(r['candidate_count'],1437);self.assertEqual(r['self_exclusion_count'],0)
        self.assertEqual(r['ranked_candidate_count'],0)
        self.assertTrue(all(not rows for rows in r['modes'].values()))
        self.assertEqual(list(r['weights'].values()),[.25]*4)
        for kind in ['a','c1','c2']:self.assertIn('hf_merged_00209',self.g.maps[kind])

    def test_no_query_fitting_and_no_mutation(self):
        before=deepcopy(self.params);h=digest(f.OUT/'calibration/median_params.json')
        for key in ['cfd_final_00001','hf_merged_00198']:
            result=search.search(self.g,self.params,key)
            self.assertEqual(result['medians'],before['medians'])
        self.assertEqual(self.params,before);self.assertEqual(digest(f.OUT/'calibration/median_params.json'),h)
        self.assertTrue(all(not m.flags.writeable for m in self.g.vectors.values()))

    def test_path_hash_resolution_and_unknown_query(self):
        key='cfd_final_00001';source=Path(self.g.by_id[key]['image_path'])
        self.assertEqual(self.g.resolve(source),key)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'renamed.png';shutil.copyfile(source,p);self.assertEqual(self.g.resolve(p),key)
            p.write_bytes(b'new bytes')
            with self.assertRaises(ValueError):self.g.resolve(p)
            with self.assertRaises(ValueError):self.g.resolve(Path(folder)/source.name)
        with self.assertRaises(ValueError):self.g.resolve('unknown.png')
        with self.assertRaises(ValueError):self.g.resolve('cfd_final_00001.wrong_extension')

    def test_fourway_rejects_AB_calibration(self):
        with self.assertRaisesRegex(ValueError,'schema/version/fingerprint/ID'):
            f.load_calibration(self.g,f.AB_CALIBRATION)

    def test_calibration_identity_schema_version_and_fingerprint_guards(self):
        changes=dict(schema_id='old_schema',feature_versions={},fingerprint={},image_ids=self.g.ids[::-1],
                     pair_ids_sha256='bad',epsilon=1e-6,epsilon_c1=1e-6)
        with tempfile.TemporaryDirectory() as folder:
            for key,value in changes.items():
                p=deepcopy(self.params);p[key]=value;write_json(Path(folder)/'median_params.json',p)
                with self.subTest(key=key),self.assertRaises(ValueError):f.load_calibration(self.g,folder)

    def test_saved_median_and_pair_file_guards(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);shutil.copyfile(f.OUT/'calibration/representative_pairs.csv',folder/'representative_pairs.csv')
            p=deepcopy(self.params);p['medians']['c1']+=.01;write_json(folder/'median_params.json',p)
            with self.assertRaisesRegex(ValueError,'median disagrees'):f.load_calibration(self.g,folder)
            write_json(folder/'median_params.json',self.params);(folder/'representative_pairs.csv').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'CSV hash mismatch'):f.load_calibration(self.g,folder)

    def test_trial_C1_C2_cannot_substitute_full_galleries(self):
        # Trial C1 has v0.2 binding and must fail existing loader's lock.
        with self.assertRaises((ValueError,FileNotFoundError,KeyError)):
            f.C1Gallery(f.ROOT/'outputs/C1_lbp/trial100_spec_v0_1')
        trial_c2=f.C2Gallery(f.ROOT/'outputs/C2_hog/trial100')
        with patch.object(f,'C2Gallery',return_value=trial_c2),self.assertRaisesRegex(ValueError,'counts'):
            f.FourGallery()

    def test_feature_schema_and_manifest_mismatch(self):
        for gallery_class,gallery in [(f.C1Gallery,self.g.c1),(f.C2Gallery,self.g.c2)]:
            manifest=deepcopy(gallery.manifest);manifest['feature_version']='wrong_feature'
            with tempfile.TemporaryDirectory() as folder:
                write_json(Path(folder)/'manifest.json',manifest)
                with self.assertRaisesRegex(ValueError,'mismatch'):gallery_class(folder)

    def test_refuse_existing_outputs_calibration_and_outside_namespace(self):
        with self.assertRaises(FileExistsError):f.build_calibration(self.g)
        r=search.search(self.g,self.params,'cfd_final_00001')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):search.save_run(self.g,r,folder)
        with tempfile.TemporaryDirectory(dir=f.OUT/'queries') as folder:
            with self.assertRaises(FileExistsError):search.save_run(self.g,r,folder)


if __name__=='__main__':unittest.main()
