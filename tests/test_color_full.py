"""Input lineage, approved configuration and full-gallery query contracts."""
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import digest
from features.B_color.src.color_features import SCHEMA as OLD_SCHEMA
from features.B_color.src.full_color import SCHEMA, verified_input, descriptor_checks, new_output
from features.B_color.src.search_full_color import rank, load_gallery


class FullColorTests(unittest.TestCase):
    def test_approved_schema_is_separate_from_historical_trials(self):
        self.assertEqual(SCHEMA['id'],'B144_raw_v1.0.0')
        self.assertEqual(SCHEMA['mask_variant'],'raw');self.assertFalse(SCHEMA['erosion_for_features'])
        self.assertEqual((SCHEMA['skin_class'],SCHEMA['hair_class']),(1,17))
        self.assertEqual(SCHEMA['minimum_region_pixels'],100)
        self.assertFalse(SCHEMA['saturation_filter']);self.assertFalse(SCHEMA['normalization']['query_refit'])
        self.assertEqual(SCHEMA['normalization']['profile'],'all144')
        self.assertNotEqual(OLD_SCHEMA['id'],SCHEMA['id'])
        self.assertNotIn('mask_variant',OLD_SCHEMA)

    def fixture_input(self, folder):
        folder = Path(folder); dataset=folder/'dataset'; uniface=folder/'uniface'
        (dataset/'images').mkdir(parents=True);(uniface/'receipts').mkdir(parents=True)
        name='cfd_final_00001.png';stem=Path(name).stem
        image=np.zeros((256,256,3),np.uint8);image[:128]=(0,0,255);image[128:]=(255,0,0)
        cv2.imwrite(str(dataset/'images'/name),image)
        hashes={};metric={'status':'success','skin_pixels':32768,'hair_pixels':32768}
        for region in ('skin','hair'):
            mask=np.zeros((256,256),np.uint8)
            if region=='skin':mask[:128]=255
            else:mask[128:]=255
            relative=f'masks/{region}/{stem}_{region}_mask.png'
            path=uniface/relative;path.parent.mkdir(parents=True)
            cv2.imwrite(str(path),mask);hashes[relative]=digest(path)
        row={'image_name':name,'source_sha256':digest(dataset/'images'/name)}
        receipt={'source_sha256':row['source_sha256'],'row':dict(metric,image_name=name),'artifacts':hashes}
        (uniface/'receipts'/f'{stem}.json').write_text(json.dumps(receipt),encoding='utf-8')
        return dataset,uniface,row,metric

    def test_only_verified_raw_masks_are_loaded_without_clean_or_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            dataset,uniface,row,metric=self.fixture_input(folder)
            image,skin,hair,lineage=verified_input(dataset,uniface,row,metric)
            self.assertEqual(image.shape,(256,256,3));self.assertEqual(lineage['skin_pixels'],32768)
            self.assertTrue(np.all(skin[:128]==255));self.assertTrue(np.all(hair[128:]==255))
            self.assertFalse((uniface/'masks/skin_clean').exists())

    def test_corrupt_raw_mask_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            dataset,uniface,row,metric=self.fixture_input(folder)
            path=uniface/'masks/skin/cfd_final_00001_skin_mask.png'
            cv2.imwrite(str(path),np.zeros((256,256),np.uint8))
            with self.assertRaisesRegex(ValueError,'raw-mask hash mismatch'):
                verified_input(dataset,uniface,row,metric)

    def test_saved_counts_are_not_trusted_without_pixel_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            dataset,uniface,row,metric=self.fixture_input(folder);metric['hair_pixels']=123
            with self.assertRaisesRegex(ValueError,'pixel-count mismatch'):
                verified_input(dataset,uniface,row,metric)

    def test_descriptor_invariants_reject_post_zscore_or_invalid_histograms(self):
        raw=np.zeros((3,144));raw[:,[0,60,72,132]]=1
        self.assertTrue(descriptor_checks(raw)['finite'])
        for index in (0,60,72,132):
            broken=raw.copy();broken[0,index]=0
            with self.assertRaises(ValueError):descriptor_checks(broken)
        broken=raw.copy();broken[0,71]=1.1
        with self.assertRaises(ValueError):descriptor_checks(broken)

    def test_id_exclusion_and_filename_ties_with_independent_3_4_5_oracle(self):
        z=np.zeros((4,144));z[1,[0,143]]=[3,4];z[2,[0,143]]=[-3,-4];z[3,71]=12
        rows=[{'image_id':i,'image_name':n,'dataset_source':'HF'} for i,n in
              [('same-id','renamed.png'),('b-id','b.png'),('a-id','a.png'),('far-id','far.png')]]
        q=np.zeros(144)
        found=rank(q,z,rows,'same-id')
        self.assertEqual([r['image_name'] for r in found],['a.png','b.png','far.png'])
        self.assertEqual([r['distance'] for r in found],[5,5,12])
        self.assertEqual(rank(q,z,rows,None)[0]['image_id'],'same-id')

    def test_gallery_load_reuses_hand_calculated_statistics_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            gallery=Path(folder);raw=np.zeros((3,144));raw[:,[0,60,72,132]]=1
            raw[:,48]=[1,3,5]
            mean=np.zeros(144);mean[[0,60,72,132]]=1;mean[48]=3
            std=np.ones(144);std[48]=math.sqrt(8/3)
            actual_std=np.zeros(144);actual_std[48]=math.sqrt(8/3)
            z=(raw-mean)/std
            for name,array in (('features_B_raw.npy',raw),('features_B_normalized.npy',z)):
                np.save(gallery/name,array)
            (gallery/'schema.json').write_text(json.dumps(SCHEMA),encoding='utf-8')
            with (gallery/'feature_rows.csv').open('w',newline='',encoding='utf-8') as stream:
                w=csv.DictWriter(stream,fieldnames=['image_id','image_name']);w.writeheader()
                w.writerows({'image_id':str(i),'image_name':f'{i}.png'} for i in range(3))
            (gallery/'fit_manifest.csv').write_text('feature_row_index\n0\n1\n2\n',encoding='utf-8')
            np.savez(gallery/'normalization_stats.npz',mean=mean,std=std,raw_std=actual_std,
                fit_count=3,schema_id=SCHEMA['id'],profile='all144',fit_manifest_sha256=digest(gallery/'fit_manifest.csv'))
            files=['schema.json','feature_rows.csv','features_B_raw.npy','features_B_normalized.npy','normalization_stats.npz','fit_manifest.csv']
            (gallery/'gallery_integrity.json').write_text(json.dumps({n:digest(gallery/n) for n in files}),encoding='utf-8')
            _,_,loaded,stats=load_gallery(gallery)
            self.assertAlmostEqual(loaded[0,48],-math.sqrt(1.5))
            self.assertEqual(stats['std'][0],1)
            with (gallery/'features_B_normalized.npy').open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'integrity mismatch'):load_gallery(gallery)

    def test_output_guard_rejects_input_descendants(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):new_output(Path(folder)/'not_allowed')
        from features.B_color.src.audit_color_inputs import ROOT
        protected=ROOT/'outputs/B_color/uniface_full'
        with self.assertRaisesRegex(ValueError,'overlaps'):new_output(protected/'new_child',(protected,))


if __name__=='__main__':unittest.main()
