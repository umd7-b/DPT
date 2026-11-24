"""Real SQLite constraints, byte integrity, calibration isolation and fusion parity."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from database import four_feature as four
from database import store
from retrieval import fusion_four as fusion
from retrieval import search_fusion as file_search


class FourFeatureDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file=fusion.FourGallery();cls.params=fusion.load_calibration(cls.file)
        cls.source=store.connect(four.DEFAULT_DB)

    @classmethod
    def tearDownClass(cls):cls.source.close()

    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
        self.source.backup(self.c);self.c.execute('PRAGMA foreign_keys=ON')

    def tearDown(self):self.c.close()

    def test_coverage_and_eye_history(self):
        g=four.SqlFourGallery(self.c)
        self.assertEqual(len(g.ids),1437)
        for k in fusion.KINDS:self.assertEqual(len(g.valid[k]),self.file.policy['expected_counts'][k])
        self.assertEqual(self.c.execute('SELECT count(*) FROM EyeCoordinates').fetchone()[0],1441)
        self.assertEqual(self.c.execute('SELECT count(*) FROM EyeMetadataAuditV1').fetchone()[0],1438)
        self.assertEqual(self.c.execute('PRAGMA user_version').fetchone()[0],1)

    def test_all_vector_bytes_roundtrip_exact(self):
        g=four.SqlFourGallery(self.c)
        for k in fusion.KINDS:
            for key,(i,row) in self.file.maps[k].items():
                expected=self.file.sources[k][1][i];actual=g.valid[k][key]
                self.assertEqual(actual.dtype.str,expected.dtype.str)
                self.assertEqual(actual.tobytes(),expected.tobytes())

    def test_full_rankings_all_modes_CFD_HF(self):
        g=four.SqlFourGallery(self.c)
        for key in ['cfd_final_00001','hf_merged_00001']:
            sql=four.query(self.c,key,top_k=2000,persist=False,gallery=g)
            files=file_search.search(self.file,self.params,key,2000)
            self.assertEqual(sql['modes'],files['modes'])
            self.assertEqual(sql['candidate_count'],1436);self.assertEqual(sql['self_exclusion_count'],1)

    def test_missing_B_persists_unavailable_no_results(self):
        r=four.query(self.c,'hf_merged_00209')
        self.assertEqual(r['status'],'fusion_unavailable');self.assertEqual(r['missing_feature'],'missing_B')
        self.assertEqual(r['ranked_candidate_count'],0);self.assertEqual(r['candidate_count'],1437)
        self.assertTrue(all(not v for v in r['modes'].values()))
        self.assertEqual(self.c.execute('SELECT count(*) FROM FourFeatureResults WHERE run_id=?',(r['run_id'],)).fetchone()[0],0)
        self.assertEqual(self.c.execute('SELECT count(*) FROM FourFeatureRunComponents WHERE run_id=?',(r['run_id'],)).fetchone()[0],4)
        row=self.c.execute("SELECT * FROM FeatureVectors WHERE image_id='hf_merged_00209' AND feature_version=?",(self.params['feature_versions']['b'],)).fetchone()
        self.assertIsNone(row['vector_data']);self.assertIsNone(row['feature_row_index'])

    def test_INSERT_SELECT_run_results_versions_weights(self):
        before=self.c.execute('SELECT count(*) FROM FourFeatureRuns').fetchone()[0]
        r=four.query(self.c,'cfd_final_00001')
        self.assertEqual(self.c.execute('SELECT count(*) FROM FourFeatureRuns').fetchone()[0],before+1)
        saved=self.c.execute('SELECT * FROM FourFeatureRuns WHERE run_id=?',(r['run_id'],)).fetchone()
        self.assertEqual([saved['weight_'+k] for k in fusion.KINDS],[.25]*4)
        components=list(self.c.execute('SELECT * FROM FourFeatureRunComponents WHERE run_id=?',(r['run_id'],)))
        self.assertEqual({x['kind']:x['feature_version'] for x in components},r['feature_versions'])
        for mode,results in r['modes'].items():
            rows=list(self.c.execute('SELECT * FROM FourFeatureResults WHERE run_id=? AND mode=? ORDER BY rank',(r['run_id'],mode)))
            self.assertEqual([x['image_id'] for x in rows],[x['image_id'] for x in results])
            for a,b in zip(rows,results,strict=True):
                self.assertEqual(a['D'],b['D']);self.assertEqual(a['dC1'],b['distance_c1']);self.assertEqual(a['score'],b['score'])

    def test_invalid_weights_do_not_insert(self):
        before=self.c.execute('SELECT count(*) FROM FourFeatureRuns').fetchone()[0]
        for weights in [(1,1,1,1),(-1,1,1,0),(np.nan,0,0,1),(np.inf,0,0,1)]:
            with self.assertRaises(ValueError):four.query(self.c,'cfd_final_00001',weights=weights)
        self.assertEqual(self.c.execute('SELECT count(*) FROM FourFeatureRuns').fetchone()[0],before)

    def test_foreign_keys_unique_and_null_missing_payload(self):
        version=self.params['feature_versions']['c1']
        for sql,values in [
            ('INSERT INTO FeatureVectors SELECT * FROM FeatureVectors WHERE image_id=? AND feature_version=?',('cfd_final_00001',version)),
            ('UPDATE FeatureVectors SET feature_version=? WHERE image_id=? AND feature_version=?',('absent','cfd_final_00001',version)),
            ('UPDATE FeatureVectors SET image_id=? WHERE image_id=? AND feature_version=?',('absent','cfd_final_00001',version)),
            ("UPDATE FeatureVectors SET vector_data=zeroblob(1152) WHERE status='missing'",()),
            ('INSERT INTO CalibrationComponents SELECT * FROM CalibrationComponents WHERE calibration_id=?',(four.CALIBRATION_ID,))]:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):self.c.execute(sql,values)
        self.assertFalse(self.c.execute('PRAGMA foreign_key_check').fetchall())

    def test_dtype_dimension_constraints(self):
        version=self.params['feature_versions']['c2']
        for field,value in [('dtype','<f4'),('dimension',236),('vector_data',b'bad')]:
            with self.subTest(field=field),self.assertRaises(sqlite3.IntegrityError):
                self.c.execute('UPDATE FeatureVectors SET '+field+'=? WHERE image_id=? AND feature_version=?',(value,'cfd_final_00001',version))

    def test_corrupt_vector_bytes_rejected_even_when_hash_updated(self):
        v=self.params['feature_versions']['c1']
        row=self.c.execute("SELECT vector_data FROM FeatureVectors WHERE image_id='cfd_final_00001' AND feature_version=?",(v,)).fetchone()
        payload=bytearray(row[0]);payload[0]^=1;payload=bytes(payload)
        self.c.execute("UPDATE FeatureVectors SET vector_data=?,vector_sha256=? WHERE image_id='cfd_final_00001' AND feature_version=?",(payload,store.sha_bytes(payload),v))
        with self.assertRaisesRegex(ValueError,'Vector source'):four.SqlFourGallery(self.c)

    def test_wrong_feature_schema_and_artifact_hash(self):
        v=self.params['feature_versions']['c1']
        self.c.execute('UPDATE FeatureVersions SET schema_hash=? WHERE feature_version=?',('0'*64,v))
        with self.assertRaisesRegex(ValueError,'version/schema'):four.SqlFourGallery(self.c)

    def test_corrupt_embedded_artifact_rejected(self):
        self.c.execute("UPDATE FourFeatureArtifacts SET artifact_data=? WHERE artifact_name='feature_schema.json'",(b'changed',))
        with self.assertRaisesRegex(ValueError,'artifact/source hash'):four.SqlFourGallery(self.c)

    def test_calibration_isolation_and_median_tamper(self):
        with self.assertRaisesRegex(ValueError,'isolation'):four.SqlFourGallery(self.c,store.CALIBRATION_ID)
        self.c.execute('UPDATE CalibrationComponents SET median=median+0.01 WHERE calibration_id=? AND feature_version=?',
                       (four.CALIBRATION_ID,self.params['feature_versions']['c1']))
        with self.assertRaisesRegex(ValueError,'component version/median'):four.SqlFourGallery(self.c)
        self.assertEqual(store.load_calibration(self.c),self.file.ab_params)

    def test_calibration_pair_distance_and_blob_tamper(self):
        self.c.execute('UPDATE CalibrationPairDistances SET distance=distance+0.1 WHERE calibration_id=? AND pair_index=0',
                       (four.CALIBRATION_ID,))
        with self.assertRaisesRegex(ValueError,'pair distance'):four.SqlFourGallery(self.c)

    def test_row_order_permutation(self):
        # Physically rebuild the valid bindings in reverse insertion order in RAM.
        original=list(self.c.execute('SELECT * FROM FourFeatureVectorBindings'))
        self.c.execute('DELETE FROM FourFeatureVectorBindings')
        self.c.executemany('INSERT INTO FourFeatureVectorBindings VALUES (?,?,?,?,?)',[tuple(r) for r in original[::-1]])
        self.c.execute('PRAGMA reverse_unordered_selects=ON')
        sql=four.query(self.c,'hf_merged_00198',top_k=2000,persist=False)
        self.assertEqual(sql['modes'],file_search.search(self.file,self.params,'hf_merged_00198',2000)['modes'])

    def test_sql_query_does_not_read_file_vectors_or_calibration(self):
        original=np.load
        def guard(file,*args,**kwargs):
            if isinstance(file,(str,Path)):raise AssertionError('SQL adapter read feature file: '+str(file))
            return original(file,*args,**kwargs)  # Existing NPZ stats read from SQLite BytesIO are allowed.
        with patch.object(np,'load',side_effect=guard),patch.object(fusion,'load_calibration',side_effect=AssertionError('file calibration')):
            r=four.query(self.c,'cfd_final_00001',persist=False)
        self.assertEqual(r['status'],'ok')

    def test_result_constraints_self_pool_unavailable_and_rank(self):
        r=four.query(self.c,'cfd_final_00001')
        row=dict(self.c.execute('SELECT * FROM FourFeatureResults WHERE run_id=? LIMIT 1',(r['run_id'],)).fetchone())
        missing=four.query(self.c,'hf_merged_00209')
        for record in [row,dict(row,rank=6),dict(row,rank=2,image_id='cfd_final_00001'),
                       dict(row,rank=2,image_id='hf_merged_00209'),dict(row,run_id=missing['run_id'])]:
            with self.subTest(record=record),self.assertRaises(sqlite3.IntegrityError):store.insert_row(self.c,'FourFeatureResults',record)

    def test_backup_restore_and_refuse_existing_import(self):
        with tempfile.TemporaryDirectory() as folder:
            backup=Path(folder)/'backup.sqlite3';restore=Path(folder)/'restored.sqlite3'
            store.backup(four.DEFAULT_DB,backup);store.backup(backup,restore)
            with closing(store.connect(restore)) as c:
                self.assertEqual(four.query(c,'cfd_final_00001',persist=False)['modes'],
                                 four.query(self.c,'cfd_final_00001',persist=False)['modes'])
                self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
            with self.assertRaises(FileExistsError):store.backup(four.DEFAULT_DB,backup)
        with self.assertRaises(FileExistsError):four.import_database(four.DEFAULT_DB)


if __name__=='__main__':unittest.main()
