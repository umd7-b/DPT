"""Independent equations and intermediate numerical checks before C2 batching."""
import math
import unittest
import numpy as np
from features.C2_hog.src import root_hog as hog
from features.C2_hog.verification import scalar_oracle as oracle


class RootHOGTests(unittest.TestCase):
    def test_ROI_exact_shape_pixels_and_input_unchanged(self):
        image=np.random.default_rng(49).integers(0,256,(256,256,3),np.uint8);before=image.copy()
        roi=hog.extract_face_roi(image)
        self.assertEqual(roi.shape,(192,160,3));np.testing.assert_array_equal(roi,image[32:224,48:208])
        roi[0,0]=0;np.testing.assert_array_equal(image,before)

    def test_grayscale_integer_colors_matches_C1_convention(self):
        from features.C1_lbp.src.lbp236 import grayscale
        image=np.random.default_rng(11).integers(0,256,(192,160,3),np.uint8)
        np.testing.assert_array_equal(hog.convert_to_gray(image),grayscale(image))
        image[:,:5]=np.array([[255,0,0],[0,255,0],[0,0,255],[255,255,255],[0,0,0]])
        np.testing.assert_array_equal(hog.convert_to_gray(image)[0,:5],[29,150,76,255,0])

    def test_horizontal_vertical_diagonal_gradients(self):
        yy,xx=np.indices((192,160))
        for gray,dx,dy,theta in [(xx,2.,0.,0.),(yy,0.,2.,90.),(xx+yy,2.,2.,45.)]:
            gx,gy=hog.compute_gradients(gray.astype(np.float64));m,a=hog.compute_magnitude_orientation(gx,gy)
            np.testing.assert_array_equal(gx[1:-1,1:-1],dx);np.testing.assert_array_equal(gy[1:-1,1:-1],dy)
            np.testing.assert_allclose(m[1:-1,1:-1],math.sqrt(dx*dx+dy*dy),rtol=0,atol=1e-15)
            np.testing.assert_array_equal(a[1:-1,1:-1],theta)

    def test_central_differences_not_Sobel_and_zero_border(self):
        gray=np.zeros((192,160));gray[60,71]=13;gray[60,69]=3;gray[61,70]=17;gray[59,70]=2
        gx,gy=hog.compute_gradients(gray)
        self.assertEqual(gx[60,70],10);self.assertEqual(gy[60,70],15)
        for array in [gx,gy]:
            self.assertFalse(array[[0,-1],:].any());self.assertFalse(array[:,[0,-1]].any())

    def test_unsigned_orientations_and_180_wrap(self):
        gx=np.ones((192,160));gy=np.zeros_like(gx)
        gx[20,20]=-1;gy[20,21]=-1;gx[20,21]=0;gx[20,22]=-1;gy[20,22]=-1
        _,a=hog.compute_magnitude_orientation(gx,gy)
        self.assertEqual(a[20,20],0.);self.assertEqual(a[20,21],90.);self.assertEqual(a[20,22],45.)
        self.assertTrue(np.all((a>=0)&(a<180)))

    def test_all9_hard_bins_boundaries(self):
        m=np.zeros((192,160));a=m.copy()
        for b in range(9):m[10,10+b]=b+1;a[10,10+b]=20.*b
        m[10,25]=10;a[10,25]=np.nextafter(180.,0.)
        cells=hog.compute_cell_histograms(m,a);expected=np.arange(1,10,dtype=np.float64);expected[8]+=10
        np.testing.assert_array_equal(cells[0,0],expected);self.assertEqual(cells.sum(),55.)

    def test_16_cells40x48_no_spatial_interpolation(self):
        m=np.ones((192,160));a=np.zeros_like(m);c=hog.compute_cell_histograms(m,a)
        self.assertEqual(c.shape,(4,4,9));np.testing.assert_array_equal(c[:,:,0],40*48);self.assertFalse(c[:,:,1:].any())

    def test_block9x36_and_cell_bin_order(self):
        c=np.arange(144,dtype=np.float64).reshape(4,4,9);b=hog.build_blocks(c)
        self.assertEqual(b.shape,(9,36))
        np.testing.assert_array_equal(b[0],np.concatenate([c[0,0],c[0,1],c[1,0],c[1,1]]))
        np.testing.assert_array_equal(b[8],np.concatenate([c[2,2],c[2,3],c[3,2],c[3,3]]))

    def test_Root_block_L1_not_block_L2_or_Hys(self):
        b=np.zeros((9,36));b[:,0]=1;b[:,1]=3;r=hog.root_normalize_blocks(b)
        self.assertAlmostEqual(r[0,0],math.sqrt(1/(4+1e-8)));self.assertAlmostEqual(r[0,1],math.sqrt(3/(4+1e-8)))
        self.assertNotAlmostEqual(r[0,0],1/math.sqrt(10));self.assertNotEqual(float(r[0,1]),.2)

    def test_epsilon_zero_block_and_global_L2(self):
        b=np.zeros((9,36));b[0,0]=1e-10;b[1,1]=1e-9;r=hog.root_normalize_blocks(b)
        self.assertAlmostEqual(r[0,0],math.sqrt(1e-10/(1e-10+1e-8)));self.assertEqual(float(r[2].sum()),0.)
        v=hog.normalize_final_vector(r);self.assertEqual(v.shape,(324,));self.assertEqual(v.dtype,np.float64)
        self.assertAlmostEqual(float(np.linalg.norm(v)),1.,places=15)

    def test_zero_gradient_missing_not_fake_vector(self):
        r=hog.extract_c2(np.full((256,256,3),81,np.uint8))
        self.assertEqual(r['status'],'missing_C2');self.assertIsNone(r['vector']);self.assertIn('zero_',r['missing_reason'])
        self.assertTrue(np.isfinite(r['root_blocks']).all());self.assertEqual(float(r['cells'].sum()),0.)

    def test_bad_input_NaN_no_imputation(self):
        for image in [None,np.zeros((192,160,3),np.uint8),np.full((256,256,3),np.nan)]:
            r=hog.extract_c2(image);self.assertEqual(r['status'],'missing_C2');self.assertIsNone(r['vector'])
        with self.assertRaises(ValueError):hog.compute_gradients(np.full((192,160),np.nan))

    def test_independent_scalar_complete_random_image(self):
        image=np.random.default_rng(234).integers(0,256,(256,256,3),np.uint8)
        a,b=hog.extract_c2(image),oracle.extract(image)
        for k in ['gray','gx','gy']:np.testing.assert_array_equal(a[k],b[k])
        np.testing.assert_allclose(a['cells'],b['cells'],rtol=1e-13,atol=1e-8)
        for k in ['root_blocks','vector']:np.testing.assert_allclose(a[k],b[k],rtol=0,atol=5e-14)

    def test_Euclid_not_cosine_or_squared(self):
        a=np.zeros(324);b=np.zeros(324);a[0]=1;b[1]=1
        self.assertEqual(hog.euclidean(a,a),0.);self.assertEqual(hog.euclidean(a,b),hog.euclidean(b,a))
        self.assertAlmostEqual(hog.euclidean(a,b),math.sqrt(2));self.assertAlmostEqual(hog.euclidean(a,b),oracle.euclid(a,b))
        self.assertGreaterEqual(hog.euclidean(a,b),0.)

    def test_spec_content_and_source_versioned(self):
        s=hog.load_spec();self.assertEqual(s['content_sha256'],hog.SPEC_PIN)
        self.assertEqual(hog.lock()['preprocessing_id'],hog.PREPROCESSING)


if __name__=='__main__':unittest.main()
