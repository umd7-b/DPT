"""Batch behavior uses temporary synthetic fixtures, never dataset GT."""
import csv
import json
from importlib.util import find_spec
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from features.B_color.src import batch_uniface as batch


class BatchUniFaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_sampling_reproducible_balanced_unique(self):
        for prefix in ('cfd_final_','hf_merged_'):
            for i in range(60): (self.root/f'{prefix}{i:05d}.png').touch()
        first = batch.select_images(self.root,42)
        self.assertEqual(first,batch.select_images(self.root,42))
        self.assertEqual(len(first),100)
        self.assertEqual(len({p.name for p,_ in first}),100)
        self.assertEqual(sum(s=='CFD' for _,s in first),50)
        self.assertEqual(sum(s=='HF' for _,s in first),50)
        self.assertNotEqual(first,batch.select_images(self.root,43))

    def test_short_group_is_not_replaced(self):
        for prefix,count in [('cfd_final_',60),('hf_merged_',49)]:
            for i in range(count): (self.root/f'{prefix}{i:05d}.png').touch()
        with self.assertRaisesRegex(ValueError,'HF.*found 49'):
            batch.select_images(self.root)

    def test_masks_preserve_raw_and_use_exact_erosion(self):
        labels=np.zeros((256,256),np.uint8)
        labels[20:100,40:150]=1; labels[2:18,80:160]=17; labels[200,100]=10
        original=labels.copy()
        masks=batch.make_masks(labels)
        np.testing.assert_array_equal(labels,original)
        for region,class_id in [('skin',1),('hair',17)]:
            raw=(labels==class_id).astype(np.uint8)*255
            np.testing.assert_array_equal(masks[region],raw)
            np.testing.assert_array_equal(masks[region+'_clean'],cv2.erode(raw,np.ones((3,3),np.uint8),iterations=1))
        for mask in masks.values():
            self.assertEqual(mask.shape,(256,256)); self.assertEqual(mask.dtype,np.uint8)
            self.assertTrue(set(np.unique(mask)).issubset({0,255}))
        self.assertEqual(masks['skin'][200,100],0) # Nose class is separate, as in the existing script.

    def test_reject_bad_parser_output(self):
        for value in (np.zeros((32,32),np.uint8),np.zeros((256,256),np.float32),np.full((256,256),99,np.uint8)):
            with self.assertRaises(ValueError): batch.make_masks(value)

    def test_empty_and_thin_masks_warn_without_fake_ratios(self):
        labels=np.zeros((256,256),np.uint8);labels[80,80]=17
        masks=batch.make_masks(labels)
        numbers,flags=batch.quality(masks)
        self.assertIn('empty',flags['skin'])
        self.assertEqual(numbers['erosion_skin_loss_ratio'],'')
        self.assertIn('large_erosion_loss',flags['hair_clean'])
        self.assertEqual(numbers['erosion_hair_loss_ratio'],1)

    def test_batch_reuses_parser_continues_after_failure_and_protects_sources(self):
        dataset=self.root/'dataset'; (dataset/'images').mkdir(parents=True);(dataset/'skin_masks').mkdir()
        selected=[]
        for name in ('cfd_final_good.png','hf_merged_broken.png','hf_merged_good.png'):
            p=dataset/'images'/name
            if 'broken' in name: p.write_bytes(b'not a png')
            else: cv2.imwrite(str(p),np.full((256,256,3),100,np.uint8))
            selected.append((p,'CFD' if name.startswith('cfd') else 'HF'))
        (dataset/'skin_masks/original.png').write_bytes(b'protected existing data')
        before=batch.protected_hashes(dataset)
        calls=[]
        class Parser:
            def parse(self,image):
                calls.append(1)
                labels=np.zeros((256,256),np.uint8)
                labels[80:200,70:190]=1;labels[10:60,50:210]=17
                return labels
        factories=[]
        def factory():
            factories.append(1)
            return Parser(),{'model':'synthetic fixture; no weights'}
        output=self.root/'results'
        result=batch.run_batch(selected,dataset,output,factory)
        self.assertEqual(len(factories),1);self.assertEqual(len(calls),2)
        self.assertEqual(result['successful'],2);self.assertEqual(result['failed'],1)
        self.assertEqual(before,batch.protected_hashes(dataset))
        self.assertEqual(result['changed_original_files'],[])
        self.assertEqual(len(list(output.glob('masks/*/*.png'))),8)
        self.assertTrue((output/'masks/hair_clean/cfd_final_good_hair_clean_mask.png').exists())
        self.assertTrue((output/'contact_sheet/page_01.png').exists())
        with (output/'metrics.csv').open(encoding='utf-8-sig') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),3);self.assertEqual(rows[1]['status'],'failed')
        self.assertEqual(rows[1]['hair_pixels'],'')
        self.assertEqual(rows[2]['status'],'success')
        with self.assertRaises(FileExistsError): batch.run_batch(selected,dataset,output,factory)
        with self.assertRaises(ValueError): batch.run_batch(selected,dataset,dataset/'images/results',factory)

    @unittest.skipUnless(find_spec('uniface'), 'UniFace environment required')
    def test_missing_local_weights_never_initializes_or_downloads(self):
        with patch('uniface.model_store.get_cache_dir',return_value=str(self.root)), patch('uniface.parsing.BiSeNet') as constructor:
            with self.assertRaisesRegex(FileNotFoundError,'Downloads disabled'): batch.create_parser()
            constructor.assert_not_called()

    @unittest.skipUnless(find_spec('uniface'), 'UniFace environment required')
    def test_corrupt_weights_are_not_replaced(self):
        p=self.root/'parsing_resnet18.onnx';p.write_bytes(b'bad weights')
        with patch('uniface.model_store.get_cache_dir',return_value=str(self.root)), patch('uniface.parsing.BiSeNet') as constructor:
            with self.assertRaisesRegex(ValueError,'mismatch'): batch.create_parser()
            constructor.assert_not_called()
        self.assertEqual(p.read_bytes(),b'bad weights')


if __name__=='__main__': unittest.main()
