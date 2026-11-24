"""Numerical tests use synthetic color pixels, not segmentation ground truth."""
import unittest
import numpy as np
import cv2
from features.B_color.src.color_features import (region_descriptor,extract_color,hue_statistics,
    fit_standardizer,transform,feature_names)
from features.B_color.src.run_color_experiment import build_nose_masks


class ColorFeatureTests(unittest.TestCase):
    def test_red_histogram_bins_and_CIE_Lab_units(self):
        image=np.full((10,10,3),(0,0,255),np.uint8);mask=np.full((10,10),255,np.uint8)
        v,info=region_descriptor(image,mask)
        self.assertEqual(v.shape,(72,));self.assertEqual(np.argmax(v[:48]),3)
        self.assertEqual(v[3],1);self.assertEqual(v[60],1)
        self.assertAlmostEqual(v[48],53.24,delta=.2)
        self.assertAlmostEqual(v[52],80.09,delta=.3)
        self.assertAlmostEqual(v[56],67.2,delta=.3)
        self.assertEqual(v[49],0);self.assertEqual(v[51],0)
        self.assertAlmostEqual(v[70],0);self.assertAlmostEqual(v[71],0)

    def test_excluded_pixels_and_black_padding_never_enter_features(self):
        rng=np.random.default_rng(2);image=rng.integers(0,256,(20,20,3),dtype=np.uint8)
        mask=np.zeros((20,20),np.uint8);mask[5:15,5:15]=255
        v,_=region_descriptor(image,mask)
        changed=image.copy();changed[mask==0]=0
        np.testing.assert_array_equal(v,region_descriptor(changed,mask)[0])
        changed[mask==0]=255
        np.testing.assert_array_equal(v,region_descriptor(changed,mask)[0])

    def test_actual_selected_black_pixels_are_counted(self):
        image=np.zeros((10,10,3),np.uint8);mask=np.full((10,10),255,np.uint8)
        v,info=region_descriptor(image,mask)
        self.assertEqual(v[0],1);self.assertEqual(info['pixels'],100)
        self.assertIn('low_saturation_hue_unreliable',info['warnings'])

    def test_hue_wrap_and_uniform_resultant_are_finite(self):
        mean,std,r,w=hue_statistics([179,1])
        self.assertAlmostEqual(mean,0,places=10);self.assertLess(std,.02)
        mean,std,r,w=hue_statistics([0,45,90,135])
        self.assertEqual(mean,0);self.assertEqual(std,1)
        self.assertTrue(w);self.assertLess(r,1e-8)

    def test_histogram_endpoint_bins_are_not_dropped(self):
        hsv=np.tile(np.array([[[179,255,255],[0,0,255]]],np.uint8),(10,5,1))
        image=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR);mask=np.full(image.shape[:2],255,np.uint8)
        v,_=region_descriptor(image,mask)
        self.assertAlmostEqual(v[47],.5);self.assertAlmostEqual(v[0],.5)
        self.assertAlmostEqual(v[69],.5);self.assertAlmostEqual(v[60],.5)
        self.assertAlmostEqual(v[:48].sum(),1);self.assertAlmostEqual(v[60:70].sum(),1)

    def test_dimension_layout_and_input_immutability(self):
        rng=np.random.default_rng(3);im=rng.integers(0,256,(20,20,3),dtype=np.uint8)
        skin=np.zeros((20,20),np.uint8);skin[:10]=255
        hair=np.zeros_like(skin);hair[10:]=255
        before=[a.copy() for a in (im,skin,hair)]
        result=extract_color(im,skin,hair)
        self.assertEqual(result.vector.shape,(144,));self.assertTrue(np.isfinite(result.vector).all())
        self.assertEqual(len(set(feature_names())),144)
        np.testing.assert_array_equal(result.vector[:72],region_descriptor(im,skin)[0])
        for actual,expected in zip((im,skin,hair),before):np.testing.assert_array_equal(actual,expected)

    def test_two_equal_mass_colors_have_population_skew_zero_kurtosis_one(self):
        im=np.zeros((10,10,3),np.uint8);im[:5]=(0,0,255);im[5:]=(255,0,0)
        mask=np.full((10,10),255,np.uint8)
        v,_=region_descriptor(im,mask)
        for offset in (48,52,56):
            self.assertGreater(v[offset+1],0)
            self.assertAlmostEqual(v[offset+2],0,places=10)
            self.assertAlmostEqual(v[offset+3],1,places=10)

    def test_missing_regions_return_none_not_zero_vector(self):
        im=np.zeros((20,20,3),np.uint8);skin=np.zeros((20,20),np.uint8);skin[:10]=255
        hair=np.zeros_like(skin)
        r=extract_color(im,skin,hair);self.assertIsNone(r.vector);self.assertEqual(r.hair['status'],'missing_empty')
        hair[15,15]=255;r=extract_color(im,skin,hair)
        self.assertIsNone(r.vector);self.assertEqual(r.hair['status'],'insufficient_pixels')

    def test_invalid_masks_and_overlap_rejected(self):
        im=np.zeros((20,20,3),np.uint8);m=np.ones((20,20),np.uint8)*255
        with self.assertRaises(ValueError):extract_color(im,m,m)
        with self.assertRaises(ValueError):region_descriptor(im,np.full(m.shape,128,np.uint8))
        with self.assertRaises(ValueError):region_descriptor(im,np.zeros((2,2),np.uint8))

    def test_standardization_uses_only_fitted_gallery_statistics(self):
        rng=np.random.default_rng(4);x=rng.normal(size=(20,144));x[:,2]=5
        stats=fit_standardizer(x);z=transform(x,stats)
        np.testing.assert_allclose(z[:,3:].mean(axis=0),0,atol=1e-12)
        np.testing.assert_allclose(z[:,3:].std(axis=0),1,atol=1e-12)
        self.assertTrue(np.all(z[:,2]==0))
        query=x[0]+2
        np.testing.assert_allclose(transform(query,stats),(query-stats['mean'])/stats['std'])
        for invalid in (np.zeros((2,143)),np.full((2,144),np.nan)):
            with self.assertRaises(ValueError):fit_standardizer(invalid)

    def test_moments_only_profile_keeps_histograms_unchanged(self):
        x=np.random.default_rng(1).uniform(size=(10,144));stats=fit_standardizer(x,'moments_only');z=transform(x,stats)
        np.testing.assert_array_equal(z[:,:48],x[:,:48]);np.testing.assert_array_equal(z[:,60:120],x[:,60:120])

    def test_nose_union_uses_real_class10_labels_only(self):
        image=np.zeros((4,4,3),np.uint8);labels=np.zeros((4,4),np.uint8)
        labels[0,0]=1;labels[1,1]=10;labels[2,2]=17;labels[3,3]=14
        skin,hair=build_nose_masks(image,labels)
        self.assertEqual(np.count_nonzero(skin),2);self.assertEqual(np.count_nonzero(hair),1)
        self.assertEqual(skin[3,3],0);self.assertEqual(skin[1,1],255)


if __name__=='__main__':unittest.main()
