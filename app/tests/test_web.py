"""Real HTTP, SQL parity, image identity and immutable snapshot integration tests."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from app.server import AppServer,PortraitService,IMAGE_ROOT,DATABASE_SHA256
from database import four_feature as four
from database import store
from shared.report_v2 import read_json


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=PortraitService();cls.server=AppServer(('127.0.0.1',0),cls.service)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        assert store.digest(four.DEFAULT_DB)==DATABASE_SHA256

    def http(self,path,body=None,method=None,headers=None):
        h={'X-Application-Token':self.service.token,'Content-Type':'application/json',**(headers or {})}
        data=json.dumps(body,allow_nan=False).encode() if body is not None else None
        request=Request(self.base+path,data=data,method=method,headers=h)
        try:response=urlopen(request,timeout=15)
        except HTTPError as error:response=error
        with response:
            payload=response.read();kind=response.headers.get('Content-Type','')
            return response.status,json.loads(payload) if 'json' in kind else payload,response.headers

    def test_overview_real_counts_medians_and_modes(self):
        status,result,_=self.http('/api/overview');self.assertEqual(status,200)
        self.assertEqual((result['image_count'],result['valid_vectors'],result['missing_vectors'],result['comparison_pool']),(1438,5751,1,1437))
        self.assertEqual(result['medians'],self.service.gallery.params['medians'])
        self.assertEqual(result['default_weights'],dict.fromkeys(four.fusion.KINDS,.25))
        self.assertTrue(result['readonly']);self.assertFalse(result['history_enabled']);self.assertFalse(result['new_image_support'])

    def test_default_top5_parity_all_six_queries_and_all_modes(self):
        for key in ['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00198','hf_merged_00722','hf_merged_00209']:
            with self.subTest(key=key):
                status,result,_=self.http('/api/search',dict(image=key+'.png',mode='compare'))
                self.assertEqual(status,200)
                expected=read_json(four.BASE/'queries'/(key+'.json'))
                for field in ['status','weights','medians','candidate_count','self_exclusion_count','ranked_candidate_count']:
                    self.assertEqual(result[field],expected[field])
                for mode,rows in result['modes'].items():
                    clean=[{k:v for k,v in r.items() if k!='image_url'} for r in rows]
                    self.assertEqual(clean,expected['modes'][mode])
                    self.assertNotIn(key,[r['image_id'] for r in rows])
                self.assertEqual(result['query']['image_url'],'/media/'+key)
                self.assertIsNone(result['run_id']);self.assertFalse(result['history_saved'])

    def test_query_and_all_top5_images_match_image_id_hash(self):
        _,result,_=self.http('/api/search',dict(image='cfd_final_00001'))
        entries=[result['query']]+[r for rows in result['modes'].values() for r in rows]
        for row in entries:
            status,payload,headers=self.http(row['image_url'])
            self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'image/png')
            self.assertEqual(hashlib.sha256(payload).hexdigest(),self.service.catalog[row['image_id']]['image_hash'])

    def test_custom_weights_forwarded_unchanged_and_repeatable(self):
        weights=dict(a=.1,b=.2,c1=.3,c2=.4);body=dict(image='hf_merged_00001',weights=weights)
        _,first,_=self.http('/api/search',body);_,second,_=self.http('/api/search',body)
        self.assertEqual(first,second);self.assertEqual(first['weights'],weights)
        with closing(self.service.connect()) as c:
            expected=four.query(c,'hf_merged_00001',persist=False,gallery=self.service.gallery,weights=[.1,.2,.3,.4])
        for mode,rows in first['modes'].items():
            self.assertEqual([{k:v for k,v in r.items() if k!='image_url'} for r in rows],expected['modes'][mode])

    def test_bad_weights_rejected_not_renormalized(self):
        for weights in [dict(a=.5,b=.5,c1=.5,c2=.5),dict(a=-.1,b=.1,c1=.5,c2=.5),
                        dict(a='NaN',b=.25,c1=.25,c2=.25),dict(a=True,b=0,c1=0,c2=0),dict(a=1),
                        dict(a=10**400,b=0,c1=0,c2=0)]:
            with self.subTest(weights=weights):
                status,result,_=self.http('/api/search',dict(image='cfd_final_00001',weights=weights))
                self.assertEqual(status,422);self.assertEqual(result['error']['code'],'invalid_weights')

    def test_nonfinite_json_and_invalid_json_refused(self):
        for data in [b'NaN',b'{"image":"cfd_final_00001","weights":{"a":NaN}}',b'not-json']:
            request=Request(self.base+'/api/search',data=data,headers={'X-Application-Token':self.service.token,'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as error:urlopen(request,timeout=5)
            self.assertEqual(error.exception.code,400)

    def test_missing_B_explicit_no_three_way(self):
        _,r,_=self.http('/api/search',dict(image='hf_merged_00209',weights=dict(a=1,b=0,c1=0,c2=0)))
        self.assertEqual(r['status'],'fusion_unavailable');self.assertEqual(r['missing_feature'],'missing_B')
        self.assertEqual(r['available_features'],['a','c1','c2']);self.assertTrue(all(not rows for rows in r['modes'].values()))

    def test_database_ro_query_only_and_history_unchanged(self):
        with closing(self.service.connect()) as c:
            before=four.summary(c)
            self.assertEqual(c.execute('PRAGMA query_only').fetchone()[0],1)
            with self.assertRaises(sqlite3.OperationalError):c.execute("UPDATE Images SET filename='forbidden'")
        for _ in range(3):self.assertEqual(self.http('/api/search',dict(image='cfd_final_00001'))[0],200)
        with closing(self.service.connect()) as c:self.assertEqual(four.summary(c),before)
        self.assertEqual(store.digest(four.DEFAULT_DB),DATABASE_SHA256)

    def test_path_traversal_and_private_files_never_served(self):
        for path in ['/../database/schema.sql','/%2e%2e/database/schema.sql','/%252e%252e/database/schema.sql',
                     '/media/..%5c..%5ccsdldpt.pdf','/app/server.py','/database/schema.sql','/media/C%3a%5cWindows%5cwin.ini']:
            with self.subTest(path=path):self.assertIn(self.http(path)[0],(404,422))
        for value in ['../cfd_final_00001.png','D:\\secret.png','/etc/passwd','cfd_final_00001.png/..']:
            self.assertEqual(self.http('/api/search',dict(image=value))[0],422)

    def test_bad_host_origin_token_and_write_routes(self):
        self.assertEqual(self.http('/api/overview',headers={'Host':'evil.test'})[0],403)
        self.assertEqual(self.http('/api/search',dict(image='cfd_final_00001'),headers={'Origin':'https://evil.test'})[0],403)
        self.assertEqual(self.http('/api/search',dict(image='cfd_final_00001'),headers={'X-Application-Token':'wrong'})[0],403)
        self.assertEqual(self.http('/api/images/cfd_final_00001',{},method='PUT')[0],405)
        self.assertEqual(self.http('/api/images/cfd_final_00001',{},method='DELETE')[0],405)
        self.assertEqual(self.http('/api/upload',{})[0],405)

    def test_invalid_inputs_and_filters_clear_errors(self):
        for body,status in [(dict(image='unknown.png'),404),(dict(image=3),422),(dict(image='cfd_final_00001',mode='AB'),422),
                            (dict(image='cfd_final_00001',top_k=0),422),(dict(image='cfd_final_00001',path='secret'),422)]:
            actual,result,_=self.http('/api/search',body);self.assertEqual(actual,status);self.assertTrue(result['error']['message'])
        for path in ['/api/gallery?limit=999999','/api/gallery?source=other','/api/gallery?offset=bad','/api/gallery?q=a&q=b']:
            self.assertEqual(self.http(path)[0],422)

    def test_pagination_and_metadata_real_no_inferred_HF_person(self):
        _,r,_=self.http('/api/gallery?source=HF&limit=10&offset=10');self.assertEqual(r['total'],728);self.assertEqual(len(r['items']),10)
        self.assertTrue(all(x['source']=='hf' or x['source']=='HF' for x in r['items']))
        _,detail,_=self.http('/api/images/hf_merged_00209');self.assertIsNone(detail['person']);self.assertIsNone(detail['metadata']['person_id'])
        self.assertEqual(len(detail['features']),4);self.assertEqual(sum(f['status']=='missing' for f in detail['features']),1)
        self.assertTrue(all(r['coordinate_role']=='audit_remeasurement' for r in detail['eye_measurements']))

    def test_missing_or_changed_image_errors_without_source_edits(self):
        row=self.service.catalog['cfd_final_00001']
        with patch.dict(row,image_path=str(IMAGE_ROOT/'web_test_missing.png')):
            status,result,_=self.http('/media/cfd_final_00001');self.assertEqual(status,404);self.assertEqual(result['error']['code'],'image_missing')
        with patch.dict(row,image_path=str(Path('C:/Windows/win.ini'))):self.assertEqual(self.http('/media/cfd_final_00001')[0],403)
        original=Path.read_bytes
        def changed(path):return b'corrupt' if path.resolve()==Path(row['image_path']).resolve() else original(path)
        with patch.object(Path,'read_bytes',changed):self.assertEqual(self.http('/media/cfd_final_00001')[0],409)

    def test_static_security_headers_and_no_fake_upload(self):
        status,html,headers=self.http('/');self.assertEqual(status,200)
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff');self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertNotIn(b'type="file"',html);self.assertIn('Ảnh mới: chưa hỗ trợ'.encode('utf8'),html)


if __name__=='__main__':unittest.main()
