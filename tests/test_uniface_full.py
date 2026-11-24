"""Full-mode/retry tests use only synthetic images and temporary predictions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import cv2
import numpy as np

from features.B_color.src import batch_uniface as b


class FullUniFaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.dataset=self.root/'dataset'
        (self.dataset/'images').mkdir(parents=True)
        (self.dataset/'skin_masks').mkdir()
        self.selected=[]
        for index in range(3):
            name=('cfd_final_' if index<2 else 'hf_merged_')+f'{index:05d}.png'
            path=self.dataset/'images'/name
            cv2.imwrite(str(path),np.full((256,256,3),50+index,np.uint8))
            self.selected.append((path,'CFD' if index<2 else 'HF'))
        self.output=self.root/'output'

    def tearDown(self):self.temp.cleanup()

    @staticmethod
    def labels():
        result=np.zeros((256,256),np.uint8)
        result[50:180,70:190]=1
        result[10:40,40:200]=17
        return result

    def factory(self):
        return Mock(parse=Mock(return_value=self.labels())), {'model':'synthetic'}

    def hashes(self):
        return {p.relative_to(self.output).as_posix():(b.sha256(p),p.stat().st_mtime_ns)
                for p in (self.output/'masks').glob('*/*.png')}

    def test_all_selection_is_sorted_and_includes_both_sources(self):
        first=b.select_all_images(self.dataset/'images')
        self.assertEqual(first,b.select_all_images(self.dataset/'images'))
        self.assertEqual(len(first),3)
        cv2.imwrite(str(self.dataset/'images/unknown.png'),np.zeros((256,256,3),np.uint8))
        with self.assertRaises(ValueError):b.select_all_images(self.dataset/'images')

    def test_retry_failed_skips_verified_masks_and_reuses_one_parser(self):
        parser=Mock();parser.parse.side_effect=[self.labels(),RuntimeError('transient inference error'),self.labels()]
        factory=Mock(return_value=(parser,{'model':'synthetic'}))
        result=b.run_batch(self.selected,self.dataset,self.output,factory,split_sources=True)
        self.assertEqual(result['successful'],2)
        factory.assert_called_once();self.assertEqual(parser.parse.call_count,3)
        failed_path=self.output/'masks/skin'/f'{self.selected[1][0].stem}_skin_mask.png'
        self.assertFalse(failed_path.exists())
        before=self.hashes()
        new_parser=Mock(parse=Mock(return_value=self.labels()))
        new_factory=Mock(return_value=(new_parser,{'model':'synthetic'}))
        result=b.run_batch(self.selected,self.dataset,self.output,new_factory,resume=True,split_sources=True)
        self.assertEqual(result['successful'],3)
        self.assertEqual(result['verified_images_skipped'],2)
        self.assertEqual(result['inference_images_this_attempt'],1)
        new_factory.assert_called_once();new_parser.parse.assert_called_once()
        after=self.hashes()
        self.assertTrue(all(after[p]==data for p,data in before.items()))
        self.assertEqual(result['validation']['valid_masks'],12)
        self.assertEqual(result['contact_pages'],2)

    def test_completed_retry_never_initializes_parser_or_rewrites_masks(self):
        b.run_batch(self.selected,self.dataset,self.output,self.factory)
        before=self.hashes();factory=Mock(side_effect=AssertionError('Must not initialize'))
        result=b.run_batch(self.selected,self.dataset,self.output,factory,resume=True)
        factory.assert_not_called()
        self.assertEqual(result['inference_images_this_attempt'],0)
        self.assertEqual(self.hashes(),before)

    def test_changed_input_rejected_before_retry(self):
        b.run_batch(self.selected,self.dataset,self.output,self.factory)
        self.selected[0][0].write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError,'Original inputs changed'):
            b.run_batch(self.selected,self.dataset,self.output,self.factory,resume=True)

    def test_corrupted_mask_is_flagged_and_never_overwritten(self):
        b.run_batch(self.selected,self.dataset,self.output,self.factory)
        path=next((self.output/'masks/skin').glob('*.png'))
        path.write_bytes(b'corrupt artifact')
        factory=Mock(side_effect=AssertionError('Must not regenerate corrupt verified files'))
        result=b.run_batch(self.selected,self.dataset,self.output,factory,resume=True)
        self.assertEqual(result['failed'],1)
        self.assertEqual(path.read_bytes(),b'corrupt artifact')
        factory.assert_not_called()
        self.assertTrue(result['validation']['unexpected_or_partial_mask_files'])

    def test_failed_model_startup_is_attempted_only_once(self):
        factory=Mock(side_effect=RuntimeError('startup failure'))
        result=b.run_batch(self.selected,self.dataset,self.output,factory)
        self.assertEqual(result['failed'],3)
        factory.assert_called_once()
        self.assertFalse(list((self.output/'masks').glob('*/*.png')))

    def test_pending_conflicting_artifact_is_not_replaced(self):
        parser=Mock(parse=Mock(side_effect=RuntimeError('temporary')))
        b.run_batch(self.selected,self.dataset,self.output,lambda:(parser,{'model':'synthetic'}))
        target=b.output_masks(self.output,self.selected[0][0].name)['skin']
        target.write_bytes(b'preexisting unverified output')
        result=b.run_batch(self.selected,self.dataset,self.output,self.factory,resume=True)
        self.assertEqual(result['failed'],1)
        self.assertEqual(target.read_bytes(),b'preexisting unverified output')

    def test_model_change_on_retry_cannot_mix_predictions(self):
        parser=Mock(parse=Mock(side_effect=RuntimeError('temporary')))
        b.run_batch(self.selected,self.dataset,self.output,lambda:(parser,{'model':'synthetic'}))
        changed_factory=Mock(return_value=(Mock(),{'model':'different'}))
        result=b.run_batch(self.selected,self.dataset,self.output,changed_factory,resume=True)
        self.assertEqual(result['failed'],3)
        changed_factory.assert_called_once()
        self.assertFalse(list((self.output/'masks').glob('*/*.png')))

    def test_full_cli_cannot_target_batch100(self):
        self.assertEqual(b.main(['--all','--output',str(b.DEFAULT_OUTPUT)]),1)


if __name__=='__main__':unittest.main()
