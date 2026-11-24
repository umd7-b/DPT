"""New independent A oracles; detecting a known deviation is a passing audit test."""
import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch
from common import *
from features.A_geometry.src import geometry_features as a
from features.A_geometry.src import normalize_features as standardizer


def points():
    p=np.zeros((68,2),np.float32)
    values={36:(0,0),37:(1,-1),38:(3,-1),39:(4,0),40:(3,1),41:(1,1),
        42:(8,0),43:(9,-1),44:(11,-1),45:(12,0),46:(11,1),47:(9,1),
        21:(5,-2),22:(7,-2),8:(6,10),2:(-2,4),14:(14,4),4:(0,8),12:(12,8),
        31:(4,3),35:(8,3),30:(6,4),48:(3,6),54:(9,6),62:(6,5),66:(6,7)}
    for i,value in values.items():p[i]=value
    return p


class LandmarkOracles(unittest.TestCase):
    def test_normalization_known_centers_and_ipd(self):
        actual,d=a.normalize_landmarks(points())
        self.assertEqual(d,8.)
        np.testing.assert_array_equal(actual[8],[0.,1.25])
        np.testing.assert_array_equal(actual[36],[-.75,0.])

    def test_translation_and_scale_invariance(self):
        expected,_=a.normalize_landmarks(points())
        actual,_=a.normalize_landmarks(points()*3+100)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=2e-7)

    def test_zero_eye_distance_rejected(self):
        with self.assertRaises(ValueError):a.normalize_landmarks(np.zeros((68,2),np.float32))

    def test_angle_right_straight_and_degenerate(self):
        self.assertAlmostEqual(a.angle_degrees(np.array([1.,0]),np.zeros(2),np.array([0.,1])),90)
        self.assertAlmostEqual(a.angle_degrees(np.array([-1.,0]),np.zeros(2),np.array([1.,0])),180)
        with self.assertRaises(ValueError):a.angle_degrees(np.zeros(2),np.zeros(2),np.ones(2))

    def test_flatten_order_x_y_and_136_plus_14(self):
        with patch.object(a,'detect_landmarks',return_value=points()):
            vector,coords,ratios,_=a.extract_geometry(Path('synthetic.png'))
        self.assertEqual(vector.shape,(150,))
        np.testing.assert_array_equal(coords[16:18],[0,1.25])
        np.testing.assert_array_equal(vector[:136],coords)
        np.testing.assert_array_equal(vector[136:],ratios)


class RatioOracles(unittest.TestCase):
    pass


# Analytic operands chosen by hand, independent of the code or scalar_a2().
operands=[(16,12),(8,12),(4,8),(4,8),(4,8),(4,8),(4,8),(6,8),(2,8),
          (4,8),(6,8),(6,12),(12,12)]
def ratio_test(index):
    def test(self):
        expected=(operands[index][0]/(operands[index][1]+1e-8) if index<13
                  else math.degrees(math.acos(-.8)))
        self.assertAlmostEqual(float(a.calculate_ratios(points())[index]),expected,delta=1e-5)
    return test
for i in range(14):setattr(RatioOracles,f'test_A2_{i+1:02d}_analytic_operands',ratio_test(i))


class StandardizerOracles(unittest.TestCase):
    def run_normalizer(self,values):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            np.save(folder/'features_A_raw.npy',np.tile(np.array(values)[:,None],(1,150)))
            with patch.object(standardizer,'FEATURE_DIR',folder), contextlib.redirect_stdout(io.StringIO()):
                standardizer.main()
            with np.load(folder/'geometry_stats.npz',allow_pickle=False) as f:
                mean,std=f['mean'].copy(),f['std'].copy()
            return mean,std,np.load(folder/'features_A_normalized.npy',allow_pickle=False)

    def test_normal_sigma_detects_pdf_denominator_deviation(self):
        mean,std,z=self.run_normalizer([1,3,5])
        self.assertEqual(mean[0],3.)
        self.assertAlmostEqual(std[0],math.sqrt(8/3))
        self.assertNotEqual(std[0],math.sqrt(8/3)+1e-8)
        self.assertEqual(z.dtype,np.float32)

    def test_zero_sigma_query_proves_formulas_are_not_equivalent(self):
        mean,std,_=self.run_normalizer([7,7,7])
        actual=(9-mean[0])/std[0]
        pdf=(9-7)/(0+1e-8)
        self.assertEqual(actual,2.)
        self.assertEqual(pdf,200000000.)

    def test_small_sigma_does_not_become_sigma_plus_epsilon(self):
        _,std,_=self.run_normalizer([1e-10,3e-10,5e-10])
        self.assertEqual(std[0],1.)
        self.assertNotEqual(std[0],math.sqrt(8/3)*1e-10+1e-8)

    def test_real_image_stored_raw_reproduced(self):
        # Read the audit-only evidence; never overwrite the official raw gallery.
        p=np.load(EVIDENCE/'cfd_final_00001_landmarks68.npy',allow_pickle=False)
        expected,_,_=scalar_a2(p)
        raw=np.load(ROOT/'outputs/A_geometry/features/features_A_raw.npy',allow_pickle=False)
        np.testing.assert_allclose(raw[0,136:],expected,rtol=2e-6,atol=2e-5)


if __name__=='__main__':
    with (EVIDENCE/'unit_tests_a.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f'A independent audit tests: {result.testsRun}; failures={len(result.failures)} errors={len(result.errors)}')
    raise SystemExit(not result.wasSuccessful())
