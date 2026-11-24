import unittest
import cv2
import numpy as np
from features.B_color.src.color_features import fit_standardizer,transform,region_descriptor
from features.B_color.src.evaluate_color_retrieval import select_queries,verify_normalization,check_conventions

class ColorEvaluationTests(unittest.TestCase):
    def test_source_balanced_deterministic_query_selection(self):
        x=np.random.default_rng(9).normal(size=(16,144))
        rows=[{'image_name':f'{i:02d}.png','dataset_source':'CFD' if i<8 else 'HF'} for i in range(16)]
        selected=select_queries(x,rows)
        self.assertEqual(selected,select_queries(x,rows));self.assertEqual(len(set(selected)),10)
        self.assertEqual(sum(rows[i]['dataset_source']=='CFD' for i in selected),5)
        before=x.copy();select_queries(x,rows);np.testing.assert_array_equal(x,before)

    def test_saved_divisor_one_for_constant_columns(self):
        x=np.random.default_rng(3).normal(size=(20,144));x[:,0]=7;x[:,1]=0
        stats=fit_standardizer(x);z=transform(x,stats)
        result=verify_normalization(x,z,stats)
        self.assertEqual(result['exact_zero_variance_count'],2)
        self.assertEqual(result['near_zero_max_abs_z'],0)
        self.assertEqual(result['max_reconstruction_error'],0)

    def test_wrong_statistics_or_query_vectors_are_detected(self):
        x=np.random.default_rng(6).normal(size=(20,144));stats=fit_standardizer(x);z=transform(x,stats)
        bad={k:v.copy() if isinstance(v,np.ndarray) else v for k,v in stats.items()};bad['std'][2]*=2
        with self.assertRaises(AssertionError):verify_normalization(x,z,bad)
        changed=z.copy();changed[0,0]+=.1
        with self.assertRaises(AssertionError):verify_normalization(x,changed,stats)

    def test_independent_convention_audit_detects_excess_kurtosis(self):
        image=np.random.default_rng(7).integers(0,256,(20,20,3),dtype=np.uint8)
        mask=np.full((20,20),255,np.uint8);v,_=region_descriptor(image,mask)
        result=check_conventions(image,mask,v)
        self.assertLess(result['L_kurtosis_error'],1e-10)
        self.assertLess(result['circular_std_error'],1e-12)
        bad=v.copy();bad[51]-=3
        with self.assertRaises(AssertionError):check_conventions(image,mask,bad)

if __name__=='__main__':unittest.main()
