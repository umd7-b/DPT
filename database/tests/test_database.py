"""Numerical, relational and actual full-corpus SQLite integration tests."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

import numpy as np

from database import store as db
from retrieval import search_ab_v2 as file_v2
from shared.report_v2 import read_csv, read_json


class CodecTests(unittest.TestCase):
    def test_exact_ieee_roundtrip_including_signed_zero_and_endianness(self):
        for dtype in ('<f4','<f8','>f4','>f8'):
            x = np.array([0.,-0.,1e-30,-2.5,37.125],dtype=dtype)
            blob,stored,checksum = db.encode_vector(x,5)
            actual = db.decode_vector(blob,stored,5,checksum)
            self.assertEqual(actual.dtype.str,x.dtype.str)
            self.assertEqual(actual.tobytes(),x.tobytes())

    def test_shape_dtype_and_nonfinite_rejected(self):
        for x in (np.zeros((1,150)),np.zeros(149),np.zeros(150,dtype=np.int32),np.full(150,np.nan),np.full(150,np.inf)):
            with self.assertRaises(ValueError):
                db.encode_vector(x,150)

    def test_decode_rejects_corruption_and_wrong_dimension(self):
        blob,dtype,h = db.encode_vector(np.arange(150,dtype=np.float64),150)
        for payload,dt,dim,checksum in [(blob[:-1],dtype,150,h),(blob,dtype,144,h),
                (blob,'object',150,h),(blob,dtype,150,'0'*64)]:
            with self.assertRaises(ValueError):
                db.decode_vector(payload,dt,dim,checksum)


class DatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='portrait_database_tests_')
        cls.base = Path(cls.folder.name)/'base.sqlite3'
        cls.imported = db.import_v2(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.path = Path(self.folder.name)/f'{self._testMethodName}.sqlite3'
        # The base is closed, never modified and has no active WAL/journal.
        shutil.copyfile(self.base,self.path)
        self.c = db.connect(self.path,readonly=False)

    def tearDown(self):
        self.c.close()

    def test_actual_import_counts_and_select_identity(self):
        counts = db.counts(self.c)
        self.assertEqual((counts['Images'],counts['valid_A'],counts['valid_B']),(1438,1438,1437))
        self.assertEqual(counts['Persons'],407)
        self.assertEqual(counts['FeatureVectors'],2876)
        row = db.get_image(self.c,'cfd_final_00001')
        self.assertEqual(row['filename'],'cfd_final_00001.png')
        self.assertEqual((row['width'],row['height']),(256,256))
        self.assertIsNone(db.get_image(self.c,'hf_merged_00209')['person_id'])
        with self.assertRaises(KeyError):
            db.get_image(self.c,'unavailable')

    def test_all_vector_bytes_and_order_equal_artifacts(self):
        for kind,folder,metadata,index in [
                ('A',db.a_v2.DEFAULT_OUTPUT,'metadata.csv','a_row_index'),
                ('B',db.b_v2.DEFAULT_OUTPUT,'feature_rows.csv','feature_row_index')]:
            x = np.load(folder/f'features_{kind}_normalized.npy',allow_pickle=False)
            version = file_v2.VERSIONS[kind.lower()]
            records = read_csv(folder/metadata)
            for row in records:
                actual = db.get_vector(self.c,row['image_id'],version)
                expected = x[int(row[index])]
                self.assertEqual(actual.dtype.str,expected.dtype.str)
                self.assertEqual(actual.shape,expected.shape)
                self.assertEqual(actual.tobytes(),expected.tobytes())
        g = db.load_gallery(self.c)
        f = file_v2.load_gallery()
        self.assertEqual([r['image_id'] for r in g.rows],[r['image_id'] for r in f.rows])
        self.assertEqual(g.a.tobytes(),f.a.tobytes())
        self.assertEqual(g.b.tobytes(),f.b.tobytes())

    def test_order_after_missing_b_uses_id_not_row_zip(self):
        missing = self.c.execute("SELECT * FROM FeatureVectors WHERE image_id='hf_merged_00209' AND feature_version=?",(db.b_v2.SCHEMA_ID,)).fetchone()
        self.assertEqual(missing['a_row_index'],918)
        row = self.c.execute("SELECT * FROM FeatureVectors WHERE image_id='hf_merged_00210' AND feature_version=?",(db.b_v2.SCHEMA_ID,)).fetchone()
        self.assertEqual((row['a_row_index'],row['feature_row_index']),(919,918))
        self.assertEqual(db.load_gallery(self.c).all_a.shape,(1438,150))

    def test_normalization_npz_bytes_and_both_stages(self):
        rows = self.c.execute('SELECT * FROM NormalizationStages ORDER BY feature_version,stage_index').fetchall()
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertEqual(row['stats_data'],Path(row['source_path']).read_bytes())
        a, = db.load_stats(self.c,db.a_v2.SCHEMA_ID)
        b1,b2 = db.load_stats(self.c,db.b_v2.SCHEMA_ID)
        self.assertEqual(a['mean'].shape,(150,))
        self.assertEqual(float(a['epsilon']),1e-8)
        self.assertEqual((b1['mean'].shape,b2['mean'].shape),((24,),(144,)))

    def test_calibration_order_medians_and_all_pair_distances(self):
        params = db.load_calibration(self.c)
        self.assertEqual(params,read_json(file_v2.OUT/'calibration/median_params.json'))
        pairs = read_csv(file_v2.OUT/'calibration/representative_pairs.csv')
        actual = self.c.execute('''SELECT p.pair_index,p.image_id_1,p.image_id_2,d.feature_version,d.distance
            FROM CalibrationPairs p JOIN CalibrationPairDistances d USING(calibration_id,pair_index)
            ORDER BY p.pair_index,d.feature_version''').fetchall()
        self.assertEqual(len(actual),40000)
        for r in actual:
            source = pairs[r['pair_index']]
            kind = 'a' if r['feature_version']==db.a_v2.SCHEMA_ID else 'b'
            self.assertEqual((r['image_id_1'],r['image_id_2']),(source['image_id_1'],source['image_id_2']))
            self.assertEqual(r['distance'],float(source['distance_'+kind]))

    def test_all_saved_query_rankings_and_distances(self):
        for image_id in ('cfd_final_00001','cfd_final_00088','cfd_final_00144'):
            expected = read_json(file_v2.OUT/'queries'/image_id/'results.json')
            actual = db.search(self.c,image_id,persist=False)
            for mode,key in [('A','a_only'),('B','b_only'),('AB','ab')]:
                self.assertEqual(actual['runs'][mode]['results'],expected['results'][key])

    def test_missing_b_is_null_and_retrieval_never_zero_fills(self):
        self.assertIsNone(db.get_vector(self.c,'hf_merged_00209',db.b_v2.SCHEMA_ID))
        row = self.c.execute("SELECT status,vector_data,missing_reason FROM FeatureVectors WHERE image_id='hf_merged_00209' AND feature_version=?",(db.b_v2.SCHEMA_ID,)).fetchone()
        self.assertEqual(row['status'],'missing')
        self.assertIsNone(row['vector_data'])
        self.assertEqual(row['missing_reason'],'hair:missing_empty(0<100)')
        result = db.search(self.c,'hf_merged_00209')
        self.assertEqual(len(result['runs']['A']['results']),5)
        self.assertFalse(result['runs']['AB']['results'])
        self.assertFalse(result['runs']['B']['results'])
        for r in result['runs']['A']['results']:
            self.assertIsNone(r['distance_b'])
            self.assertIsNone(r['distance_total'])

    def test_keys_null_payload_dimension_and_row_constraints(self):
        for table,column in [('Images','image_id'),('Persons','person_id'),('FeatureVersions','feature_version'),
                             ('Calibrations','calibration_id'),('DatasetVersions','dataset_version')]:
            with self.assertRaisesRegex(sqlite3.IntegrityError,'NOT NULL'):
                self.c.execute(f'UPDATE {table} SET {column}=NULL')
        image = db.get_image(self.c,'cfd_final_00001')
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_row(self.c,'Images',image)
        record = dict(self.c.execute('SELECT * FROM FeatureVectors LIMIT 1').fetchone())
        for change in [dict(image_id='unknown'),dict(dimension=144),dict(dtype='<f4'),
                       dict(vector_data=b'bad'),dict(a_row_index=999999),dict(feature_version='absent_version')]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.c.execute('UPDATE FeatureVectors SET '+','.join(k+'=?' for k in change)+
                    ' WHERE image_id=? AND feature_version=?',
                    (*change.values(),record['image_id'],record['feature_version']))
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute("UPDATE FeatureVectors SET vector_data=zeroblob(1152) WHERE image_id='hf_merged_00209' AND status='missing'")
        self.assertEqual(self.c.execute('PRAGMA foreign_keys').fetchone()[0],1)
        self.assertFalse(self.c.execute('PRAGMA foreign_key_check').fetchall())

    def test_result_keys_candidates_and_missing_run_constraints(self):
        actual = db.search(self.c,'cfd_final_00001')
        run_id = actual['runs']['AB']['run_id']
        record = dict(self.c.execute('SELECT * FROM RetrievalResults WHERE run_id=? AND rank=1',(run_id,)).fetchone())
        for bad in [record,dict(record,rank=6),dict(record,rank=2,image_id='hf_merged_00209')]:
            with self.assertRaises(sqlite3.IntegrityError):
                db.insert_row(self.c,'RetrievalResults',bad)
        actual = db.search(self.c,'hf_merged_00209')
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_row(self.c,'RetrievalResults',dict(record,run_id=actual['runs']['B']['run_id']))

    def test_runs_results_and_query_vectors_persist_exactly(self):
        result = db.search(self.c,'cfd_final_00001',weight_a=.25,weight_b=.75)
        self.assertEqual(self.c.execute('SELECT count(*) FROM RetrievalRuns').fetchone()[0],3)
        for mode,run in result['runs'].items():
            saved = self.c.execute('SELECT * FROM RetrievalRuns WHERE run_id=?',(run['run_id'],)).fetchone()
            self.assertEqual((saved['mode'],saved['weight_a'],saved['weight_b']),(mode,.25,.75))
            for r in self.c.execute('SELECT * FROM QueryVectors WHERE run_id=?',(run['run_id'],)):
                actual = db.decode_vector(r['vector_data'],r['dtype'],r['dimension'],r['vector_sha256'])
                self.assertEqual(actual.tobytes(),db.get_vector(self.c,'cfd_final_00001',r['feature_version']).tobytes())
            rows = self.c.execute('SELECT * FROM RetrievalResults WHERE run_id=? ORDER BY rank',(run['run_id'],)).fetchall()
            self.assertEqual([r['image_id'] for r in rows],[r['image_id'] for r in run['results']])

    def test_gallery_and_query_need_no_numpy_or_csv_gallery_files(self):
        from unittest.mock import patch
        with (patch.object(file_v2,'load_gallery',side_effect=AssertionError('file gallery read')),
              patch.object(db.a_v2,'load_gallery',side_effect=AssertionError('A file gallery read'))):
            # Existing-image query takes vectors, stats and calibration from DB.
            result = db.search(self.c,'cfd_final_00001',persist=False)
        self.assertEqual(result['runs']['AB']['results'][0]['image_id'],'cfd_final_00038')

    def test_eye_measurements_are_limited_and_have_provenance(self):
        rows = self.c.execute('SELECT * FROM EyeCoordinates').fetchall()
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertEqual(row['coordinate_role'],'audit_remeasurement')
            evidence = json.loads(row['provenance_json'])
            self.assertFalse(evidence['original_preprocessing_coordinates'])
            self.assertEqual(len(evidence['model_sha256']),64)
        self.assertEqual(self.c.execute("SELECT count(*) FROM EyeCoordinates WHERE image_id='hf_merged_00209'").fetchone()[0],0)

    def test_corrupt_vector_stats_and_calibration_rejected(self):
        self.c.execute("UPDATE FeatureVectors SET vector_data=zeroblob(1200) WHERE image_id='cfd_final_00001' AND feature_version=?",(db.a_v2.SCHEMA_ID,))
        with self.assertRaises(ValueError):
            db.get_vector(self.c,'cfd_final_00001',db.a_v2.SCHEMA_ID)
        self.c.rollback()
        self.c.execute('UPDATE NormalizationStages SET stats_data=?',(b'bad',))
        with self.assertRaises(ValueError):
            db.load_stats(self.c,db.a_v2.SCHEMA_ID)
        self.c.rollback()
        self.c.execute('UPDATE CalibrationComponents SET median=median+1')
        with self.assertRaises(ValueError):
            db.load_calibration(self.c)

    def test_backup_restore_and_no_overwrite(self):
        result = db.search(self.c,'cfd_final_00001')
        backup = Path(self.folder.name)/'snapshot.sqlite3'
        restored = Path(self.folder.name)/'restored.sqlite3'
        db.backup(self.path,backup)
        db.backup(backup,restored)
        with closing(db.connect(restored)) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.counts(c),db.counts(self.c))
            again = db.search(c,'cfd_final_00001',persist=False)
            self.assertEqual(again['runs']['AB']['results'],result['runs']['AB']['results'])
        for operation in (lambda:db.import_v2(self.path),lambda:db.backup(self.path,backup)):
            with self.assertRaises(FileExistsError):
                operation()
        with self.assertRaises(ValueError):
            db.backup(self.path,self.path)

    def test_bad_query_parameters_and_unknown_id_rejected(self):
        for kwargs in [dict(top_k=0),dict(weight_a=-1,weight_b=2),dict(weight_a=.8,weight_b=.8),dict(mode='C1')]:
            with self.assertRaises(ValueError):
                db.search(self.c,'cfd_final_00001',**kwargs)
        with self.assertRaises(FileNotFoundError):
            db.search(self.c,'unknown.png')

    def test_failed_import_rolls_back_and_removes_only_new_database(self):
        from unittest.mock import patch
        destination = Path(self.folder.name)/'failed_import.sqlite3'
        with patch.object(db,'_import_eyes',side_effect=ValueError('deliberate validation failure')):
            with self.assertRaisesRegex(ValueError,'deliberate'):
                db.import_v2(destination)
        self.assertFalse(destination.exists())
        self.assertTrue(self.base.is_file())


if __name__ == '__main__':
    unittest.main()
