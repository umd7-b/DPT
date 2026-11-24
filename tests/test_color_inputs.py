import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from features.B_color.src.audit_color_inputs import align_sample,region_status,load_mask


class ColorInputTests(unittest.TestCase):
    def test_alignment_follows_A_not_random_sample(self):
        a=[{'image_name':n} for n in ('a.png','b.png','c.png')]
        full=list(reversed(a));sample=[a[2],a[0]]
        self.assertEqual(align_sample(a,full,sample),[(0,'a.png'),(2,'c.png')])

    def test_duplicates_and_missing_images_rejected(self):
        a=[{'image_name':'a.png'}]
        with self.assertRaises(ValueError):align_sample(a,a,a+a)
        with self.assertRaises(ValueError):align_sample(a,[{'image_name':'b.png'}],a)

    def test_missing_region_is_not_available(self):
        self.assertEqual(region_status(0),'missing_empty')
        self.assertEqual(region_status(4),'insufficient_pixels')
        self.assertEqual(region_status(99),'insufficient_pixels')
        self.assertEqual(region_status(100),'available_not_quality_approved')
        with self.assertRaises(ValueError):region_status(-1)

    def test_binary_mask_validation_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'mask.png';mask=np.zeros((256,256),np.uint8);mask[4:10,4:10]=255
            cv2.imwrite(str(p),mask);before=p.read_bytes()
            actual=load_mask(p,mask.shape)
            np.testing.assert_array_equal(actual,mask)
            self.assertEqual(p.read_bytes(),before)
            cv2.imwrite(str(p),np.full(mask.shape,128,np.uint8))
            with self.assertRaises(ValueError):load_mask(p,mask.shape)
            cv2.imwrite(str(p),np.zeros((16,16),np.uint8))
            with self.assertRaises(ValueError):load_mask(p,mask.shape)


if __name__=='__main__':unittest.main()
