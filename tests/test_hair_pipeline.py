"""Behavioral checks for segmentation and safe failure paths (no downloads)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import features.B_color.src.refine_hair_mask as hair


class HairPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=cv2.imread(str(hair.DATASET/'images'/hair.TARGETS[0]))
        options=hair.mp.tasks.vision.FaceLandmarkerOptions(
            base_options=hair.mp.tasks.BaseOptions(model_asset_path=str(hair.ROOT/'models/face_landmarker.task')),num_faces=1)
        cls.detector=hair.mp.tasks.vision.FaceLandmarker.create_from_options(options)
        cls.points=hair.detect_points(cls.detector,cls.image)

    @classmethod
    def tearDownClass(cls): cls.detector.close()

    def test_mask_invariants_and_no_input_mutation(self):
        original=self.image.copy(); points=self.points.copy()
        skin=cv2.imread(str(hair.DATASET/'skin_masks'/'cfd_final_00001_skin.png'),0)
        skin_before=skin.copy()
        mask,info=hair.segment_hair(self.image,self.points,skin)
        np.testing.assert_array_equal(self.image,original)
        np.testing.assert_array_equal(self.points,points)
        np.testing.assert_array_equal(skin,skin_before)
        self.assertEqual(mask.shape,original.shape[:2])
        self.assertEqual(mask.dtype,np.uint8)
        self.assertEqual(set(np.unique(mask)),{0,255})
        self.assertEqual(info['face_overlap_ratio'],0)
        self.assertGreater(np.count_nonzero(mask[180:]),500) # long hair survives below ears
        again,_=hair.segment_hair(self.image,self.points,skin)
        np.testing.assert_array_equal(mask,again)

    def test_missing_skin_uses_landmarks(self):
        mask,info=hair.segment_hair(self.image,self.points,None)
        self.assertGreater(info['hair_pixels'],0)
        self.assertEqual(info['skin_overlap_ratio'],'')

    def test_no_face_is_explicit_failure(self):
        detector=Mock(); detector.detect.return_value.face_landmarks=[]
        with self.assertRaisesRegex(ValueError,'no_face_detected'):
            hair.detect_points(detector,np.full((256,256,3),255,np.uint8))

    def test_real_detector_rejects_blank_image(self):
        with self.assertRaisesRegex(ValueError,'no_face_detected'):
            hair.detect_points(self.detector,np.full((256,256,3),255,np.uint8))

    def test_bad_skin_and_missing_skin_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'skin.png'
            self.assertIn('skin_missing_landmark_fallback',hair.read_skin(p,(256,256))[1])
            cv2.imwrite(str(p),np.zeros((10,10),np.uint8))
            self.assertIn('skin_shape_mismatch_landmark_fallback',hair.read_skin(p,(256,256))[1])
            cv2.imwrite(str(p),np.full((256,256),80,np.uint8))
            self.assertIn('skin_not_binary_landmark_fallback',hair.read_skin(p,(256,256))[1])

    def test_reject_output_inside_source(self):
        with self.assertRaises(SystemExit) as result:
            hair.main(['--image',hair.TARGETS[0],'--output-dir',str(hair.DATASET/'images')])
        self.assertEqual(result.exception.code,2)

    def test_reject_path_traversal(self):
        with self.assertRaises(SystemExit) as result:
            hair.main(['--image','../escape.png'])
        self.assertEqual(result.exception.code,2)


if __name__=='__main__': unittest.main()
