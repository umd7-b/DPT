"""Produce full-corpus import, SQL Top-5, backup/restore and baseline evidence.

Run once after import. New backup/restore paths are never overwritten. Does not
write any legacy/v2 file or recompute/replace saved vectors or fit statistics.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np

from database import store as db
from shared.report_v2 import read_csv, read_json, save_csv, write_json

ROOT = db.ROOT
E = ROOT / 'database/evidence'


def logical_hash(connection):
    h = hashlib.sha256()
    for line in connection.iterdump():
        h.update(line.encode('utf-8')); h.update(b'\n')
    return h.hexdigest()


def main():
    backup_path = ROOT/'database/backups/portrait_ab_v2.backup.sqlite3'
    restore_path = ROOT/'database/restored/portrait_ab_v2.sqlite3'
    if backup_path.exists() or restore_path.exists():
        raise FileExistsError('Verification snapshots already exist; refusing before inserting any runs')
    baseline = read_json(E/'baseline_before.json')
    assert all(db.digest(p)==h for p,h in baseline.items())
    with closing(db.connect(readonly=False)) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        records = []
        for name,folder,manifest,index in [
                ('A',db.a_v2.DEFAULT_OUTPUT,'metadata.csv','a_row_index'),
                ('B',db.b_v2.DEFAULT_OUTPUT,'feature_rows.csv','feature_row_index')]:
            version = db.v2.VERSIONS[name.lower()]
            matrix = np.load(folder/f'features_{name}_normalized.npy',allow_pickle=False)
            for row in read_csv(folder/manifest):
                saved = c.execute('SELECT * FROM FeatureVectors WHERE image_id=? AND feature_version=?',(row['image_id'],version)).fetchone()
                actual = db.get_vector(c,row['image_id'],version)
                expected = matrix[int(row[index])]
                assert actual.dtype.str == expected.dtype.str and actual.shape == expected.shape
                assert actual.tobytes() == expected.tobytes() == saved['vector_data']
                records.append(dict(image_id=row['image_id'],feature_name=name,
                    a_row_index=saved['a_row_index'],feature_row_index=saved['feature_row_index'],
                    dtype=saved['dtype'],dimension=saved['dimension'],status=saved['status'],
                    database_blob_sha256=saved['vector_sha256'],artifact_row_sha256=db.sha_bytes(expected.tobytes()),
                    exact_bytes_equal=True))
        save_csv(E/'vector_roundtrip.csv',records)
        assert len(records)==2875
        missing = dict(c.execute("SELECT image_id,feature_version,status,missing_reason,vector_data,feature_row_index FROM FeatureVectors WHERE status='missing'").fetchone())
        assert missing['image_id']=='hf_merged_00209' and missing['vector_data'] is None and missing['feature_row_index'] is None
        write_json(E/'missing_b.json',missing)
        stats = []
        for row in c.execute('SELECT * FROM NormalizationStages ORDER BY feature_version,stage_index'):
            assert row['stats_data'] == Path(row['source_path']).read_bytes()
            stats.append(dict(feature_version=row['feature_version'],stage_index=row['stage_index'],
                stage_name=row['stage_name'],exact_npz_bytes_equal=True,sha256=row['stats_sha256']))
        write_json(E/'normalization_roundtrip.json',stats)
        params = db.load_calibration(c)
        gallery = db.load_gallery(c)
        by_id = {r['image_id']:i for i,r in enumerate(gallery.rows)}
        pairs = c.execute('SELECT * FROM CalibrationPairs ORDER BY pair_index').fetchall()
        pair_rows = read_csv(db.v2.OUT/'calibration/representative_pairs.csv')
        assert [tuple(r[k] for k in ('image_id_1','image_id_2')) for r in pairs] == [(r['image_id_1'],r['image_id_2']) for r in pair_rows]
        x = np.array([(by_id[r['image_id_1']],by_id[r['image_id_2']]) for r in pairs])
        pair_errors = {}
        for kind,version,matrix in [('a',db.a_v2.SCHEMA_ID,gallery.a),('b',db.b_v2.SCHEMA_ID,gallery.b)]:
            distances = np.linalg.norm(matrix[x[:,0]]-matrix[x[:,1]],axis=1)
            saved = np.array([r[0] for r in c.execute('SELECT distance FROM CalibrationPairDistances WHERE feature_version=? ORDER BY pair_index',(version,))])
            assert np.array_equal(saved,np.array([float(r['distance_'+kind]) for r in pair_rows]))
            error = float(np.max(abs(distances-saved)))
            assert error<1e-10 and abs(float(np.median(distances))-params['median_'+kind])<1e-10
            pair_errors[kind]=error
        comparisons = []
        summaries = []
        for key in ['cfd_final_00001','cfd_final_00088','cfd_final_00144','hf_merged_00209','new_query']:
            expected = read_json(db.v2.OUT/'queries'/key/'results.json')
            actual = db.search(c,expected['query'])
            assert actual['excluded_self_ids']==expected['excluded_self_ids']
            for mode,old_key in [('A','a_only'),('B','b_only'),('AB','ab')]:
                run = actual['runs'][mode]
                assert run['results']==expected['results'][old_key]
                stored = c.execute('''SELECT t.*,i.filename FROM RetrievalResults t JOIN Images i USING(image_id)
                    WHERE run_id=? ORDER BY rank''',(run['run_id'],)).fetchall()
                assert len(stored)==len(run['results'])
                for r,old in zip(stored,expected['results'][old_key]):
                    assert r['image_id']==old['image_id'] and r['filename']==old['image_name']
                    for sql_name,file_name in [('dA','distance_a'),('dB','distance_b'),
                            ('normalized_a','normalized_a'),('normalized_b','normalized_b'),
                            ('D_AB','distance_total'),('score','score')]:
                        assert r[sql_name]==old[file_name]
                    comparisons.append(dict(query=key,mode=mode,rank=r['rank'],image_name=r['filename'],
                        file_image_id=old['image_id'],database_image_id=r['image_id'],
                        file_dA=old['distance_a'],database_dA=r['dA'],file_dB=old['distance_b'],database_dB=r['dB'],
                        file_normalized_a=old['normalized_a'],database_normalized_a=r['normalized_a'],
                        file_normalized_b=old['normalized_b'],database_normalized_b=r['normalized_b'],
                        file_D_AB=old['distance_total'],database_D_AB=r['D_AB'],
                        file_score=old['score'],database_score=r['score'],all_fields_exactly_equal=True))
                summaries.append(dict(query=key,mode=mode,run_id=run['run_id'],status=run['status'],
                    ranks_and_all_numeric_fields_equal=True,result_count=len(stored)))
            if key=='new_query':
                assert actual['query_info']['source']=='unchanged_v2_workers'
                assert '.venv311' in actual['query_info']['a']['python_executable']
                assert '.venv-uniface' in actual['query_info']['b']['python_executable']
                write_json(E/'new_query_provenance.json',actual['query_info'])
        save_csv(E/'top5_before_after.csv',comparisons)
        write_json(E/'ranking_comparison.json',summaries)
        # Demonstrate rejected SQL writes using savepoints, without retaining them.
        constraints = []
        for label,sql,values in [
            ('primary_key',"INSERT INTO Images SELECT * FROM Images WHERE image_id='cfd_final_00001'",()),
            ('person_fk',"UPDATE Images SET person_id='unknown_person' WHERE image_id='cfd_final_00001'",()),
            ('image_fk',"UPDATE FeatureVectors SET image_id='unknown_image' WHERE image_id='cfd_final_00001'",()),
            ('feature_fk',"UPDATE FeatureVectors SET feature_version='unknown_version' WHERE image_id='cfd_final_00001'",()),
            ('unique_image_feature',"INSERT INTO FeatureVectors SELECT * FROM FeatureVectors WHERE image_id='cfd_final_00001'",()),
            ('dimension_dtype_contract',"UPDATE FeatureVectors SET dimension=144 WHERE image_id='cfd_final_00001' AND feature_version=?",(db.a_v2.SCHEMA_ID,)),
            ('b_missing_not_zero_fill',"UPDATE FeatureVectors SET vector_data=zeroblob(1152) WHERE image_id='hf_merged_00209' AND feature_version=?",(db.b_v2.SCHEMA_ID,))]:
            c.execute('SAVEPOINT rejected_write')
            try:
                c.execute(sql,values)
            except sqlite3.IntegrityError as error:
                constraints.append(dict(check=label,rejected=True,error=str(error),sql=sql))
            else:
                raise AssertionError('Constraint did not reject '+label)
            finally:
                c.execute('ROLLBACK TO rejected_write'); c.execute('RELEASE rejected_write')
        write_json(E/'constraints.json',constraints)
        # Execute the supplied SQL examples with the Python sqlite3 driver.
        example_results=[]
        statement = ''
        for line in (ROOT/'database/examples.sql').read_text(encoding='utf-8').splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                cursor=c.execute(statement)
                if cursor.description:
                    example_results.append(dict(sql=statement.strip(),rows=[dict(r) for r in cursor.fetchall()]))
                statement = ''
        write_json(E/'sql_examples_results.json',example_results)
        summary = db.counts(c)
        dump_hash = logical_hash(c)
    backup_record = db.backup(db.DEFAULT_DB,backup_path)
    restore_record = db.backup(backup_path,restore_path)
    with closing(db.connect(restore_path)) as restored:
        assert logical_hash(restored)==dump_hash
        assert db.counts(restored)==summary
        assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not restored.execute('PRAGMA foreign_key_check').fetchall()
        result = db.search(restored,'cfd_final_00001',persist=False)
        assert result['runs']['AB']['results']==read_json(db.v2.OUT/'queries/cfd_final_00001/results.json')['results']['ab']
    write_json(E/'backup_restore.json',dict(backup=backup_record,restore=restore_record,
        logical_sql_dump_sha256=dump_hash,all_tables_equal=True,restored_search_equal=True,
        sqlite_integrity_check='ok',foreign_key_check=[]))
    changed = [p for p,h in baseline.items() if db.digest(p)!=h]
    assert not changed,changed
    tests=(E/'tests.log').read_text(encoding='utf-8-sig')
    assert 'Ran 19 tests' in tests and tests.rstrip().endswith('OK')
    output = dict(status='PASS',sqlite_version=sqlite3.sqlite_version,database=str(db.DEFAULT_DB),
        database_sha256=db.digest(db.DEFAULT_DB),counts=summary,exact_vector_roundtrips=len(records),
        bitwise_vector_equality=True,exact_normalization_npz_roundtrips=len(stats),
        calibration_pair_count=len(pairs),pair_euclid_max_error=pair_errors,
        comparison_modes=len(summaries),top5_result_rows=len(comparisons),all_ranking_values_exactly_equal=True,
        new_query_two_environments=True,backup_restore_verified=True,unit_integration_tests=19,
        protected_files_checked=len(baseline),changed_existing_files=changed,
        original_eye_coordinates_available=0,audit_eye_measurements=3,images_without_eye_measurements=1435,
        missing_b=missing,full_system_compliance=False,c1_c2_implemented=False)
    write_json(E/'verification_summary.json',output)
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
