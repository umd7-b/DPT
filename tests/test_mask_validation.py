"""All labels here are synthetic fixtures in temporary folders, never dataset GT."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from features.B_color.src.mask_labels import Annotation, binary_mask, digest, write_image
from features.B_color.src.annotate_masks import Editor
from features.B_color.src.evaluate_masks import evaluate, metrics
from features.B_color.src.hair_color_core import color_core
from features.B_color.src.prepare_mask_validation import select_panel


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dataset = self.root/'dataset'
        self.path = self.dataset/'images/synthetic.png'
        write_image(self.path,np.full((32,32,3),120,np.uint8))
        self.labels = self.root/'manual'
        self.pred = self.root/'predictions'
        self.pred.mkdir()
        self.annotation = Annotation(self.path,self.labels)

    def tearDown(self): self.temp.cleanup()

    def test_hand_calculated_metrics(self):
        p = np.array([[255,255],[0,0]],np.uint8)
        g = np.array([[255,0],[255,0]],np.uint8)
        result = metrics(p,g)
        self.assertAlmostEqual(result['iou'],1/3)
        self.assertEqual(result['dice'],.5)
        self.assertEqual(result['precision'],.5)
        self.assertEqual(result['recall'],.5)
        self.assertEqual((result['tp'],result['fp'],result['fn']),(1,1,1))

    def test_empty_metric_conventions(self):
        zero = np.zeros((2,2),np.uint8)
        positive = zero.copy(); positive[0,0] = 255
        self.assertEqual(metrics(zero,zero)['iou'],'')
        self.assertEqual(metrics(zero,positive)['recall'],0)
        self.assertEqual(metrics(positive,zero)['precision'],0)
        self.assertEqual(metrics(positive,zero)['recall'],'')

    def test_save_reopen_undo_and_independent_region_confirmation(self):
        a = self.annotation
        a.paint('skin',(8,8),(12,8),2)
        a.confirm('skin','synthetic_fixture_only')
        self.assertTrue(a.valid_region('skin'))
        self.assertFalse(a.valid_region('hair'))
        a.save('synthetic_fixture_only')
        reopened = Annotation(self.path,self.labels)
        np.testing.assert_array_equal(a.masks['skin'],reopened.masks['skin'])
        self.assertTrue(reopened.valid_region('skin'))
        reopened.paint('skin',(20,20),(21,20),1)
        self.assertFalse(reopened.valid_region('skin'))
        reopened.undo()
        self.assertTrue(reopened.valid_region('skin'))
        reopened.save('synthetic_fixture_only')
        self.assertEqual(len(list(reopened.directory.glob('rev_*'))),2)

    def test_overlap_edit_invalidates_both_reviews(self):
        a = self.annotation
        a.paint('skin',(8,8),(8,8),3)
        a.confirm('skin','synthetic_fixture_only')
        a.paint('hair',(8,8),(8,8),2)
        self.assertFalse(a.valid_region('skin'))
        self.assertFalse(np.any((a.masks['skin']>0)&(a.masks['hair']>0)))
        a.undo()
        self.assertTrue(a.valid_region('skin'))

    def test_empty_label_requires_explicit_absence(self):
        with self.assertRaises(ValueError): self.annotation.confirm('hair','synthetic_fixture_only')
        self.annotation.confirm('hair','synthetic_fixture_only',empty_confirmed=True)
        self.assertTrue(self.annotation.valid_region('hair'))

    def test_evaluation_never_scores_missing_or_draft(self):
        write_image(self.pred/'synthetic_hair_mask.png',np.full((32,32),255,np.uint8))
        rows = evaluate(['synthetic.png'],self.dataset,self.labels,self.pred,self.pred,self.root/'eval')
        self.assertTrue(all(r['status']=='missing_manual_label' and 'iou' not in r for r in rows))
        self.annotation.paint('hair',(5,5),(15,5),2)
        self.annotation.save('synthetic_fixture_only')
        rows = evaluate(['synthetic.png'],self.dataset,self.labels,self.pred,self.pred,self.root/'eval')
        self.assertTrue(all(r['status']=='unconfirmed_manual_label' and 'iou' not in r for r in rows))
        self.annotation.confirm('hair','synthetic_fixture_only')
        self.annotation.save('synthetic_fixture_only')
        rows = evaluate(['synthetic.png'],self.dataset,self.labels,self.pred,self.pred,self.root/'eval')
        self.assertEqual(rows[1]['status'],'evaluated')
        self.assertEqual(rows[0]['status'],'unconfirmed_manual_label')
        self.assertTrue((self.root/'eval/comparisons/synthetic_hair.png').exists())

    def test_tampered_or_wrong_source_annotations_are_rejected(self):
        a = self.annotation
        a.paint('hair',(5,5),(15,5),2); a.confirm('hair','synthetic_fixture_only'); a.save('synthetic_fixture_only')
        current = json.loads((a.directory/'current.json').read_text())['revision']
        mask_path = a.directory/current/'hair.png'
        write_image(mask_path,np.zeros((32,32),np.uint8))
        with self.assertRaisesRegex(ValueError,'hash mismatch'): Annotation(self.path,self.labels)
        rows = evaluate(['synthetic.png'],self.dataset,self.labels,self.pred,self.pred,self.root/'eval')
        self.assertTrue(all(r['status']=='invalid_manual_label' and 'iou' not in r for r in rows))

    def test_source_change_rejected(self):
        self.annotation.save('synthetic_fixture_only')
        write_image(self.path,np.zeros((32,32,3),np.uint8))
        with self.assertRaisesRegex(ValueError,'source/protocol'): Annotation(self.path,self.labels)

    def test_bad_prediction_not_scored(self):
        a = self.annotation
        a.paint('hair',(5,5),(15,5),2); a.confirm('hair','synthetic_fixture_only'); a.save('synthetic_fixture_only')
        write_image(self.pred/'synthetic_hair_mask.png',np.full((32,32),99,np.uint8))
        rows = evaluate(['synthetic.png'],self.dataset,self.labels,self.pred,self.pred,self.root/'eval')
        self.assertEqual(rows[1]['status'],'invalid_prediction')
        self.assertNotIn('iou',rows[1])

    def test_editor_mouse_navigation_does_not_confirm(self):
        other = self.dataset/'images/other.png'
        write_image(other,np.full((32,32,3),90,np.uint8))
        before = digest(self.path)
        e = Editor(['synthetic.png','other.png'],self.dataset,self.labels,'synthetic_fixture_only',self.pred)
        e.mouse(cv2.EVENT_LBUTTONDOWN,16,e.HEADER+16,0)
        e.mouse(cv2.EVENT_MOUSEMOVE,24,e.HEADER+16,0)
        e.mouse(cv2.EVENT_LBUTTONUP,24,e.HEADER+16,0)
        e.key(ord('n')); self.assertEqual(e.index,1)
        e.key(ord('b')); self.assertEqual(e.index,0)
        self.assertGreater(np.count_nonzero(e.annotation.masks['skin']),0)
        self.assertFalse(e.annotation.valid_region('skin'))
        e.key(ord('c')); e.key(ord('n')) # cancel modal, navigate
        e.key(ord('b'))
        self.assertFalse(e.annotation.valid_region('skin'))
        self.assertEqual(digest(self.path),before)

    def test_editor_confirm_requires_second_key_and_edit_revokes(self):
        e = Editor(['synthetic.png'],self.dataset,self.labels,'synthetic_fixture_only',self.pred)
        e.annotation.paint('skin',(5,5),(15,5),2)
        e.key(ord('c')); self.assertFalse(e.annotation.valid_region('skin'))
        e.key(ord('y')); self.assertTrue(e.annotation.valid_region('skin'))
        e.annotation.paint('skin',(20,20),(22,20),1)
        self.assertFalse(e.annotation.valid_region('skin'))


    def test_uppercase_confirmation_shortcuts(self):
        e = Editor(['synthetic.png'],self.dataset,self.labels,'synthetic_fixture_only',self.pred)
        e.annotation.paint('skin',(5,5),(15,5),2)
        e.key(ord('C'))
        self.assertFalse(e.annotation.valid_region('skin'))
        e.key(ord('Y'))
        self.assertTrue(e.annotation.valid_region('skin'))

    def test_color_core_is_subset_and_does_not_mutate_inputs(self):
        from features.B_color.src.refine_hair_mask import FACE_OVAL
        image = np.full((256,256,3),120,np.uint8)
        prediction = np.full((256,256),255,np.uint8)
        points = np.tile([128.,128.],(478,1)).astype(np.float32)
        for i, index in enumerate(FACE_OVAL):
            angle = 2*np.pi*i/len(FACE_OVAL)
            points[index] = (128+65*np.sin(angle),135-85*np.cos(angle))
        points[234]=(63,130); points[454]=(193,130)
        points[10]=(128,50); points[152]=(128,220)
        before_image=image.copy(); before_pred=prediction.copy()
        core = color_core(image,prediction,points)
        self.assertTrue(np.all(core<=prediction))
        self.assertEqual(np.count_nonzero(core[220:]),0)
        np.testing.assert_array_equal(image,before_image)
        np.testing.assert_array_equal(prediction,before_pred)

    def test_selection_is_deterministic_balanced_and_unique(self):
        metadata=[{'filename':f'{s}_{i}.png','source':s,'sha256':'fixture'}
                  for s in ('cfd','hf') for i in range(25)]
        features={r['filename']:np.array([i%25,i//25],np.float32) for i,r in enumerate(metadata)}
        first=select_panel(metadata,features)
        self.assertEqual(first,select_panel(metadata,features))
        self.assertEqual(len({r['filename'] for r in first}),40)
        self.assertEqual(sum(r['source']=='cfd' for r in first),20)


if __name__ == '__main__': unittest.main()
