"""Real upload/crop/native extraction/SQL query tests; no substituted gallery vectors."""
from contextlib import closing
import io
import json
from pathlib import Path
import shutil
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen

import numpy as np
from PIL import Image,ImageOps,PngImagePlugin

from app.server import AppServer,PortraitService,DATABASE_SHA256
from app.external import decode,crop_image,ExternalError,rank_external
from app import external_config as config
from database import store
from features.C1_lbp.src import lbp236
from features.C1_lbp.src.full_v04 import V04Context
from features.C1_lbp.verification import scalar_oracle as lbp_oracle
from features.C2_hog.verification import scalar_oracle as hog_oracle
from retrieval import fusion_oracle as oracle

E=config.QA_EVIDENCE


def encoded(image,fmt='PNG',**kwargs):
    b=io.BytesIO();image.save(b,format=fmt,**kwargs);return b.getvalue()


class CropDecodeTests(unittest.TestCase):
    def test_landscape_portrait_square_small_large_and_four_edges(self):
        for width,height in [(90,50),(50,90),(256,256),(800,640),(32,24)]:
            pixels=np.arange(width*height*3,dtype=np.uint32).reshape(height,width,3).astype(np.uint8)
            source=Image.fromarray(pixels);image,meta=decode(encoded(source),'image/png')
            self.assertEqual((meta['width'],meta['height']),(width,height))
            size=min(width,height)//2
            for x,y in [(0,0),(width-size,0),(0,height-size),(width-size,height-size)]:
                result=crop_image(image,x,y,size)
                self.assertEqual(result.size,(256,256))
                expected=source.crop((x,y,x+size,y+size)).resize((256,256),Image.Resampling.BICUBIC)
                np.testing.assert_array_equal(np.asarray(result),np.asarray(expected))

    def test_exif_jpeg_orientation_and_webp_decode(self):
        pixels=np.arange(30*20*3,dtype=np.uint16).reshape(20,30,3).astype(np.uint8);source=Image.fromarray(pixels)
        exif=Image.Exif();exif[274]=6;payload=encoded(source,'JPEG',exif=exif)
        actual,meta=decode(payload,'image/jpeg');self.assertEqual(actual.size,(20,30));self.assertEqual(meta['orientation'],6)
        expected=np.rot90(np.asarray(Image.open(io.BytesIO(payload)).convert('RGB')),-1)
        np.testing.assert_array_equal(np.asarray(actual),expected)
        self.assertEqual(decode(encoded(source,'WEBP'),'image/webp')[0].size,(30,20))

    def test_decode_limits_mime_and_invalid_format(self):
        payload=encoded(Image.new('RGB',(50,50),'red'))
        for data,mime in [(b'not an image','image/png'),(payload,'image/jpeg'),(encoded(Image.new('RGB',(10,10)),'GIF'),'image/gif')]:
            with self.assertRaises(ExternalError):decode(data,mime)
        with patch.object(config,'MAX_PIXELS',100),self.assertRaises(ExternalError):decode(payload,'image/png')
        with patch.object(config,'MAX_SIDE',20),self.assertRaises(ExternalError):decode(payload,'image/png')
        with patch.object(config,'MAX_UPLOAD_BYTES',10),self.assertRaises(ExternalError):decode(payload,'image/png')

    def test_crop_strict_integer_square_in_source_bounds(self):
        image=Image.new('RGB',(400,300))
        for values in [(-1,0,200),(0,0,0),(200,0,256),(0,100,256),(0.,0,100),(0,0,400)]:
            with self.subTest(values=values),self.assertRaises(ExternalError):crop_image(image,*values)

    def test_alpha_white_and_color_metadata_does_not_change_preview_decode(self):
        rgba=Image.new('RGBA',(256,256),(20,40,60,0));rgba.putpixel((0,0),(10,30,50,255))
        decoded,_=decode(encoded(rgba),'image/png')
        self.assertEqual(decoded.getpixel((0,0)),(10,30,50));self.assertEqual(decoded.getpixel((1,1)),(255,255,255))
        self.assertEqual(decoded.info,{})
        rgb=Image.new('RGB',(256,256),(30,50,70))
        decoded,_=decode(encoded(rgb,icc_profile=b'inert-test-profile'),'image/png')
        self.assertEqual(decoded.info,{});np.testing.assert_array_equal(np.asarray(decoded),np.asarray(rgb))

    def test_model_hash_failure_is_not_repaired(self):
        from app import external_worker
        with tempfile.TemporaryDirectory() as folder,patch.object(external_worker,'MODEL_SHA256','0'*64),self.assertRaisesRegex(ValueError,'model hash'):
            external_worker.extract(Path(folder)/'unused.png',Path(folder)/'rejected_model')


class ExternalHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        E.mkdir(parents=True,exist_ok=True)
        cls.service=PortraitService();cls.server=AppServer(('127.0.0.1',0),cls.service)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.base='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        assert store.digest(cls.service.database)==DATABASE_SHA256

    def http(self,path,body=None,binary=None,mime='application/json',filename='query.png'):
        payload=binary if binary is not None else json.dumps(body).encode() if body is not None else None
        headers={'Content-Type':mime,'X-File-Name':filename,'X-Application-Token':self.service.token}
        try:r=urlopen(Request(self.base+path,data=payload,headers=headers),timeout=10)
        except HTTPError as error:r=error
        with r:
            value=r.read();return r.status,json.loads(value) if 'json' in r.headers.get('Content-Type','') else value

    def prepare(self,payload,filename='query.png',crop=None):
        code,job=self.http('/api/external/upload',binary=payload,mime='image/png',filename=filename);self.assertEqual(code,201)
        width,height=job['width'],job['height'];size=min(width,height)
        rect=crop or dict(x=(width-size)//2,y=(height-size)//2,size=size)
        code,preview=self.http('/api/external/crop',dict(job_id=job['job_id'],revision=1,**rect));self.assertEqual(code,200)
        code,_=self.http('/api/external/confirm',dict(job_id=job['job_id'],revision=1));self.assertEqual(code,200)
        return job,preview

    def extract(self,job):
        code,_=self.http('/api/external/search',dict(job_id=job['job_id'],weights=dict.fromkeys(['a','b','c1','c2'],.25)));self.assertEqual(code,202)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            _,state=self.http('/api/external/jobs/'+job['job_id'])
            if not state['busy']:return state
            time.sleep(.1)
        self.fail('Real extraction timed out')

    def test_preview_bytes_equal_confirmed_backend_image(self):
        image=Image.fromarray(np.random.default_rng(42).integers(0,256,(380,620,3),np.uint8))
        job,preview=self.prepare(encoded(image),crop=dict(x=208,y=42,size=291))
        code,pixels=self.http(preview['preview_url']);self.assertEqual(code,200)
        expected=crop_image(image,208,42,291)
        np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(pixels))),np.asarray(expected))
        actual=self.service.external.get(job['job_id'])
        self.assertEqual(pixels,actual['final_path'].read_bytes());self.assertEqual(store.sha_bytes(pixels),preview['sha256'])
        self.http('/api/external/discard',dict(job_id=job['job_id']));self.assertFalse(actual['folder'].exists())

    def test_new_bytes_really_extract_all_four_and_rank_scalar_oracle(self):
        source=Image.open(self.service.catalog['cfd_final_00001']['image_path'])
        info=PngImagePlugin.PngInfo();info.add_text('external_test','different bytes, real extraction')
        job,preview=self.prepare(encoded(source,pnginfo=info),'not-in-gallery.png')
        state=self.extract(job);self.assertEqual(state['status'],'completed',state.get('error'))
        actual=self.service.external.get(job['job_id']);vectors=actual['vectors'];self.assertEqual(set(vectors),{'a','b','c1','c2'})
        for k,n in dict(a=150,b=144,c1=236,c2=324).items():self.assertEqual(vectors[k].shape,(n,));self.assertEqual(vectors[k].dtype,np.float64)
        self.assertEqual(state['result']['self_exclusion_count'],0);self.assertEqual(state['result']['candidate_count'],1437)
        self.assertNotEqual(preview['sha256'],self.service.catalog['cfd_final_00001']['image_hash'])
        # Independent scalar distances and complete ranking against every SQL candidate.
        gallery=self.service.gallery;expected={};scores={}
        for i,key in enumerate(gallery.ids):
            raw={k:(oracle.chi_square if k=='c1' else oracle.euclidean)(vectors[k],gallery.vectors[k][i]) for k in vectors}
            expected[key]=raw;scores[key]=oracle.fusion(raw,gallery.params['medians'],[.25]*4)
        for mode,rows in state['result']['modes'].items():
            order=sorted(gallery.ids,key=lambda key:(scores[key] if mode=='fusion' else expected[key][mode],key))[:5]
            self.assertEqual([r['image_id'] for r in rows],order)
            for r in rows:
                self.assertAlmostEqual(r['D'],scores[r['image_id']],places=12)
                for k in vectors:self.assertAlmostEqual(r['distance_'+k],expected[r['image_id']][k],places=12)
        # Preserve test-only evidence before the privacy cleanup removes this session.
        dest=E/'real_query_vectors'
        if dest.exists():dest=E/('real_query_vectors_'+job['job_id'])
        shutil.copytree(actual['folder']/('features_'+str(actual['revision'])),dest)
        (E/'real_query_verification.json').write_text(json.dumps(dict(status='PASS',query=state,input_sha256=actual['input_sha256'],
            crop=actual['crop'],vector_max_abs_vs_gallery={k:float(np.max(abs(vectors[k]-gallery.vectors[k][0]))) for k in vectors},
            scalar_candidates=1437,full_ranking_top5_equal=True,features_directory=str(dest)),indent=2),encoding='utf8')
        self.http('/api/external/discard',dict(job_id=job['job_id']))

    def test_exact_bytes_gallery_excludes_ID_but_filename_alone_does_not(self):
        payload=Path(self.service.catalog['cfd_final_00001']['image_path']).read_bytes()
        job,_=self.prepare(payload,'unrelated-name.png');state=self.extract(job)
        self.assertEqual(state['status'],'completed');self.assertEqual(state['result']['excluded_self_ids'],['cfd_final_00001'])
        self.assertEqual(state['result']['candidate_count'],1436)
        self.http('/api/external/discard',dict(job_id=job['job_id']))

    def test_missing_B_real_parser_no_zero_fill(self):
        payload=Path(self.service.catalog['hf_merged_00209']['image_path']).read_bytes();job,_=self.prepare(payload)
        state=self.extract(job);self.assertEqual(state['status'],'missing_feature',state.get('error'))
        self.assertEqual(state['features']['b']['status'],'missing_B');self.assertEqual(state['result']['status'],'fusion_unavailable')
        self.assertNotIn('b',self.service.external.get(job['job_id'])['vectors'])
        self.assertTrue(all(not r for r in state['result']['modes'].values()))
        (E/'missing_B_query.json').write_text(json.dumps(state,indent=2),encoding='utf8')
        self.http('/api/external/discard',dict(job_id=job['job_id']))

    def test_real_no_face_and_multiple_faces_not_fake_landmarks(self):
        blank=Image.new('RGB',(256,256),(128,128,128));multiple=Image.new('RGB',(256,256),'white')
        for i,key in enumerate(('cfd_final_00001','cfd_final_00038')):
            with Image.open(self.service.catalog[key]['image_path']) as face:
                multiple.paste(face.resize((128,128)),(i*128,64))
        for image,count in [(blank,0),(multiple,2)]:
            job,_=self.prepare(encoded(image));state=self.extract(job)
            self.assertEqual(state['status'],'failed');self.assertIsNone(state['result'])
            internal=self.service.external.get(job['job_id']);self.assertEqual(internal['extraction_provenance']['face_count'],count)
            self.assertFalse((internal['folder']/'features_1/landmarks478.npy').exists())
            self.http('/api/external/discard',dict(job_id=job['job_id']))

    def test_reject_unconfirmed_stale_crop_bad_ids_and_filename_traversal(self):
        code,_=self.http('/api/external/upload',binary=b'bad',mime='image/png');self.assertEqual(code,422)
        code,_=self.http('/api/external/upload',binary=encoded(Image.new('RGB',(10,10))),mime='image/png',filename='../attack.png');self.assertEqual(code,422)
        code,job=self.http('/api/external/upload',binary=encoded(Image.new('RGB',(20,20))),mime='image/png');self.assertEqual(code,201)
        key=job['job_id'];self.assertEqual(self.http('/api/external/search',dict(job_id=key))[0],422)
        self.assertEqual(self.http('/api/external/crop',dict(job_id=key,x=0,y=0,size=21,revision=1))[0],422)
        self.assertEqual(self.http('/api/external/crop',dict(job_id=key,x=0,y=0,size=20,revision=1))[0],200)
        self.assertEqual(self.http('/api/external/crop',dict(job_id=key,x=0,y=0,size=20,revision=1))[0],422)
        self.assertEqual(self.http('/api/external/confirm',dict(job_id=key,revision=2))[0],422)
        self.assertEqual(self.http('/api/external/jobs/../../README.md')[0],404)
        self.http('/api/external/discard',dict(job_id=key))

    def test_external_rejects_wrong_schema_hash_and_invalid_weights(self):
        job,_=self.prepare(Path(self.service.catalog['cfd_final_00001']['image_path']).read_bytes())
        key=job['job_id']
        for weights in [dict(a=.9,b=.25,c1=.25,c2=.25),dict(a=-.1,b=.6,c1=.25,c2=.25),dict(a=True,b=0,c1=0,c2=0)]:
            self.assertEqual(self.http('/api/external/search',dict(job_id=key,weights=weights))[0],422)
        # Run authentic extractors, then corrupt only the unaccepted query receipt.
        # Controller must reject it rather than use gallery vectors or stale results.
        original=self.service.external.worker
        def tampered(module,python,args,log):
            original(module,python,args,log)
            if module=='retrieval.ab_query_worker_v2':
                p=self.service.external.get(key)['folder']/'features_1/b_status.json'
                receipt=json.loads(p.read_text('utf8'));receipt['schema_id']='WRONG_SCHEMA'
                p.write_text(json.dumps(receipt),encoding='utf8')
        with patch.object(self.service.external,'worker',side_effect=tampered):
            state=self.extract(job)
        self.assertEqual(state['status'],'failed');self.assertIsNone(state['result'])
        self.assertIn('mismatch',state['error'])
        self.http('/api/external/discard',dict(job_id=key))

    def test_expiry_cleanup_only_owned_runtime(self):
        code,job=self.http('/api/external/upload',binary=encoded(Image.new('RGB',(20,20))),mime='image/png')
        internal=self.service.external.get(job['job_id']);internal['created']-=config.TTL_SECONDS+1
        self.service.external.cleanup();self.assertFalse(internal['folder'].exists())


if __name__=='__main__':unittest.main()
