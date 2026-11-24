"""New analytic color/fusion oracles, independent of the old test expected values."""
import tempfile
import unittest
from common import *
import cv2
from features.B_color.src import color_features as b
from retrieval import search_ab as ab


class ColorOracles(unittest.TestCase):
    def test_hsv_48_distinct_weighted_bins(self):
        hsv=[]
        for h in range(12):
            for s in range(4):hsv.extend([[h*15+7,s*64+32,255]]*(h*4+s+1))
        image=cv2.cvtColor(np.array(hsv,np.uint8).reshape(-1,1,3),cv2.COLOR_HSV2BGR)
        result,_=b.region_descriptor(image,np.full(image.shape[:2],255,np.uint8),min_pixels=1)
        np.testing.assert_allclose(result[:48],np.arange(1,49)/sum(range(1,49)),rtol=0,atol=1e-15)

    def test_hue_histogram_10_bins_with_known_rgb_primaries(self):
        image=np.array([[[0,0,255],[0,255,0],[255,0,0]]],np.uint8)
        vector,_=b.region_descriptor(image,np.full((1,3),255,np.uint8),min_pixels=1)
        expected=np.zeros(10);expected[[0,3,6]]=1/3
        np.testing.assert_array_equal(vector[60:70],expected)

    def test_background_outside_mask_has_no_effect(self):
        image=np.zeros((2,2,3),np.uint8);image[0,0]=[0,0,255]
        mask=np.zeros((2,2),np.uint8);mask[0,0]=255
        first,_=b.region_descriptor(image,mask,min_pixels=1)
        image[1]=[255,255,255]
        second,_=b.region_descriptor(image,mask,min_pixels=1)
        np.testing.assert_array_equal(first,second)
        self.assertEqual(first[3],1)

    def test_cie_lab_black_white_moments_analytic(self):
        image=np.array([[[0,0,0],[255,255,255]]],np.uint8)
        vector,_=b.region_descriptor(image,np.full((1,2),255,np.uint8),min_pixels=1)
        np.testing.assert_allclose(vector[48:52],[50,50,0,1],rtol=0,atol=1e-12)

    def test_lab_skew_and_pearson_kurtosis_non_excess(self):
        image=np.array([[[0,0,0],[0,0,0],[0,0,0],[255,255,255]]],np.uint8)
        vector,_=b.region_descriptor(image,np.full((1,4),255,np.uint8),min_pixels=1)
        np.testing.assert_allclose(vector[48:52],[25,25*math.sqrt(3),2/math.sqrt(3),7/3],rtol=0,atol=1e-12)

    def test_float_lab_conversion_matches_independent_srgb_xyz_equations(self):
        rgb=np.array([.9,.2,.1])
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        xyz=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])@linear
        normalized=xyz/np.array([.95047,1.,1.08883])
        delta=6/29
        f=np.where(normalized>delta**3,np.cbrt(normalized),normalized/(3*delta**2)+4/29)
        expected=np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
        actual=cv2.cvtColor(rgb[::-1].astype(np.float32).reshape(1,1,3),cv2.COLOR_BGR2LAB).reshape(3)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=.3)

    def test_circular_projection_mean_std_known_two_angles(self):
        mean,std,r,_=b.hue_statistics([0,60])
        self.assertAlmostEqual(mean,1/6)
        self.assertAlmostEqual(r,.5)
        self.assertAlmostEqual(std,math.sqrt(2*math.log(2))/(2*math.pi))

    def test_circular_wrap_boundary(self):
        mean,std,_,_=b.hue_statistics([179,1])
        self.assertTrue(mean<1e-12 or mean>1-1e-12)
        self.assertAlmostEqual(std,math.sqrt(-2*math.log(math.cos(math.pi/90)))/(2*math.pi))

    def test_undefined_resultant_convention_is_flagged(self):
        mean,std,_,warnings=b.hue_statistics([0,90])
        self.assertEqual(mean,0)
        self.assertTrue(warnings)
        self.assertEqual(std,1.)  # D07 explicitly clips this 1.183... value to [0,1].

    def test_missing_region_no_zero_fill(self):
        result=b.extract_color(np.zeros((10,10,3),np.uint8),np.full((10,10),255,np.uint8),np.zeros((10,10),np.uint8))
        self.assertIsNone(result.vector)
        self.assertEqual(result.hair['status'],'missing_empty')

    def test_b_zscore_saved_statistics_and_constant_query(self):
        matrix=np.tile(np.array([1.,3.,5.])[:,None],(1,144));matrix[:,1]=7
        stats=b.fit_standardizer(matrix)
        self.assertEqual(stats['mean'][0],3)
        self.assertAlmostEqual(stats['std'][0],math.sqrt(8/3))
        self.assertEqual(stats['std'][1],1)
        query=np.full(144,3.);query[1]=9
        out=b.transform(query,stats)
        self.assertEqual(out[0],0)
        self.assertEqual(out[1],2)


class FusionOracles(unittest.TestCase):
    def fixture(self):
        ar=[dict(image_name=n+'.png',image_path=n+'.png') for n in ['a','missing','b','c']]
        av=np.zeros((4,150));av[:,0]=[0,999,3,6]
        br=[dict(image_name=n+'.png',image_id=n,a_row_index=ai,feature_row_index=bi,status='valid')
            for n,ai,bi in [('c',3,0),('a',0,2),('b',2,1)]]
        bv=np.zeros((3,144));bv[:,0]=[8,4,0]
        return ab.join_galleries(ar,av,br,bv)

    def test_identity_join_with_missing_row_and_permuted_indices(self):
        g=self.fixture()
        np.testing.assert_array_equal(g.a[:,0],[0,3,6])
        np.testing.assert_array_equal(g.b[:,0],[0,4,8])

    def test_euclidean_not_squared_and_weighted_median_formula(self):
        g=self.fixture();qa=np.zeros(150);qa[1]=4;qb=np.zeros(144);qb[1]=3
        rows=ab.rankings(g,qa,qb,dict(median_a=2.,median_b=4.,epsilon=.5),.25,.75)['ab']
        row=next(r for r in rows if r['image_id']=='b')
        self.assertEqual(row['distance_a'],5)
        self.assertEqual(row['distance_b'],5)
        self.assertAlmostEqual(row['distance_total'],.25*5/2.5+.75*5/4.5)

    def test_pair_sample_and_known_medians(self):
        g=self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            p,_=ab.calibrate(g,folder,pair_count=100)
            self.assertEqual(p['pair_count'],3)
            self.assertEqual(p['median_a'],3)
            self.assertEqual(p['median_b'],4)
            _,reused=ab.calibrate(g,folder,pair_count=100)
            self.assertTrue(reused)

    def test_missing_b_and_self_match(self):
        g=self.fixture()
        result=ab.rankings(g,g.a[0],None,dict(median_a=3.,median_b=4.,epsilon=1e-8),exclude_ids={'a'})
        self.assertFalse(result['ab']);self.assertFalse(result['b_only'])
        self.assertEqual([r['image_id'] for r in result['a_only']],['b','c'])

    def test_no_preconcat_moment_standardization_in_current_descriptor(self):
        # Evidence for absence of the PDF-required processing stage, not approval.
        image=np.zeros((16,16,3),np.uint8);image[:8]=255
        skin=np.zeros((16,16),np.uint8);skin[:8]=255
        hair=255-skin
        vector=b.extract_color(image,skin,hair).vector
        self.assertEqual(vector[48],100.)  # Raw L*, not a gallery-normalized moment.
        self.assertEqual(vector[120],0.)


if __name__=='__main__':
    with (EVIDENCE/'unit_tests_b_ab.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f'B/AB independent audit tests: {result.testsRun}; failures={len(result.failures)} errors={len(result.errors)}')
    raise SystemExit(not result.wasSuccessful())
