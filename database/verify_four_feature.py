"""End-to-end SQL/file parity, original-row preservation, tests and backup verification."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import unittest

from database import four_feature as four
from database import store as db
from retrieval import fusion_four as f
from retrieval import search_fusion as files
from shared.report_v2 import read_json,read_csv,save_csv,write_json

E=four.BASE/'evidence'
QUERIES=['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00198','hf_merged_00722','hf_merged_00209']


def logical_hash(c):
    h=hashlib.sha256()
    for line in c.iterdump():h.update(line.encode('utf8'));h.update(b'\n')
    return h.hexdigest()


def main():
    if (E/'verification.json').exists():raise FileExistsError('Verification evidence exists; no overwrite')
    gallery=f.FourGallery();params=f.load_calibration(gallery)
    vectors=[];parity=[];top5=[];queries=[]
    with closing(db.connect(four.DEFAULT_DB)) as c,closing(db.connect(four.SOURCE_DB)) as original:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
        sql=four.SqlFourGallery(c)
        assert sql.params==params
        original_objects=list(original.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        for r in original_objects:
            actual=c.execute('SELECT type,name,sql FROM sqlite_master WHERE name=?',(r['name'],)).fetchone()
            assert tuple(actual)==tuple(r)
        preservation=[]
        append_only={'FeatureVersions','FeatureVectors','Calibrations','CalibrationComponents','CalibrationCandidates',
                     'CalibrationPairs','CalibrationPairDistances'}
        for table, in original.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            before={tuple(r) for r in original.execute('SELECT * FROM '+table)}
            after={tuple(r) for r in c.execute('SELECT * FROM '+table)}
            assert before<=after if table in append_only else before==after
            preservation.append(dict(table=table,original_rows=len(before),new_rows=len(after),
                original_rows_exact=True,policy='append_only' if table in append_only else 'unchanged'))
        for kind in f.KINDS:
            version=params['feature_versions'][kind]
            for key,(index,_) in gallery.maps[kind].items():
                expected=gallery.sources[kind][1][index];actual=sql.valid[kind][key]
                assert actual.dtype.str==expected.dtype.str and actual.shape==expected.shape and actual.tobytes()==expected.tobytes()
                stored=c.execute('SELECT * FROM FeatureVectors WHERE image_id=? AND feature_version=?',(key,version)).fetchone()
                assert stored['vector_data']==expected.tobytes() and stored['feature_row_index']==index
                vectors.append(dict(image_id=key,kind=kind,feature_version=version,source_row_index=index,
                    dtype=actual.dtype.str,dimension=len(actual),vector_sha256=db.sha_bytes(actual.tobytes()),exact_bytes=True))
        assert len(vectors)==5751
        pair_rows=read_csv(f.OUT/'calibration/representative_pairs.csv')
        for r in c.execute('SELECT * FROM CalibrationPairDistances WHERE calibration_id=?',(four.CALIBRATION_ID,)):
            kind=next(k for k,v in params['feature_versions'].items() if v==r['feature_version'])
            assert r['distance']==float(pair_rows[r['pair_index']]['distance_'+kind])
        print('All 5751 valid vectors and 80000 calibration component distances: exact',flush=True)
        for key in QUERIES:
            expected=files.search(gallery,params,key,top_k=2000)
            actual=four.query(c,key,top_k=2000,persist=False,gallery=sql)
            for field in ['status','medians','weights','epsilon','epsilon_c1','candidate_count','self_exclusion_count','ranked_candidate_count']:
                assert actual[field]==expected[field]
            assert actual['modes']==expected['modes']
            saved=read_json(four.BASE/'queries'/(key+'.json'))
            old=read_json(f.OUT/'queries'/key/'results.json')
            assert saved['modes']==old['modes']
            for field in ['status','medians','weights','candidate_count','self_exclusion_count','ranked_candidate_count']:
                assert saved[field]==old[field]
            run=c.execute('SELECT * FROM FourFeatureRuns WHERE run_id=?',(saved['run_id'],)).fetchone()
            assert run['query_image_id']==key and run['status']==saved['status']
            components=list(c.execute('SELECT * FROM FourFeatureRunComponents WHERE run_id=?',(saved['run_id'],)))
            assert {r['kind']:r['feature_version'] for r in components}==params['feature_versions']
            assert all(r['weight']==.25 and r['median']==params['medians'][r['kind']] for r in components)
            for mode in four.MODES:
                results=list(c.execute('SELECT * FROM FourFeatureResults WHERE run_id=? AND mode=? ORDER BY rank',(saved['run_id'],mode)))
                assert [r['image_id'] for r in results]==[r['image_id'] for r in saved['modes'][mode]]
                for a,b in zip(results,saved['modes'][mode],strict=True):
                    for col,field in [('dA','distance_a'),('dB','distance_b'),('dC1','distance_c1'),('dC2','distance_c2'),
                                      ('normalized_a','normalized_a'),('normalized_b','normalized_b'),
                                      ('normalized_c1','normalized_c1'),('normalized_c2','normalized_c2'),('D','D'),('score','score')]:
                        assert a[col]==b[field]
                for a,b in zip(expected['modes'][mode],actual['modes'][mode],strict=True):
                    parity.append(dict(query=key,mode=mode,rank=a['rank'],image_id=a['image_id'],
                        file_score=a['score'],sqlite_score=b['score'],file_D=a['D'],sqlite_D=b['D'],
                        **{field:b[field] for field in ['distance_a','distance_b','distance_c1','distance_c2',
                            'normalized_a','normalized_b','normalized_c1','normalized_c2']},all_fields_exact=True))
                for row in saved['modes'][mode]:top5.append(dict(query=key,**row))
            queries.append(dict(query=key,run_id=saved['run_id'],status=saved['status'],
                candidate_count=actual['candidate_count'],self_exclusion_count=actual['self_exclusion_count'],
                ranked_candidate_count=actual['ranked_candidate_count'],all_five_full_rankings_exact=True,
                result_rows=sum(len(v) for v in saved['modes'].values())))
            print('Full ranking parity:',key,actual['status'],'PASS',flush=True)
        assert len(parity)==35900 and len(top5)==125
        assert db.load_calibration(c)==db.load_calibration(original)==gallery.ab_params
        save_csv(E/'vector_roundtrip.csv',vectors);save_csv(E/'full_ranking_comparison.csv',parity);save_csv(E/'top5_before_after.csv',top5)
        write_json(E/'original_table_preservation.json',preservation)
        objects=[dict(r) for r in c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name LIKE 'FourFeature%' ORDER BY type,name")]
        columns={r['name']:[dict(x) for x in c.execute('PRAGMA table_info('+r['name']+')')] for r in objects if r['type']=='table'}
        write_json(E/'schema_inventory.json',dict(objects=objects,columns=columns,base_user_version=1,extension_version=four.EXTENSION))
        statements=[];statement=''
        for line in (four.BASE/'examples.sql').read_text('utf8').splitlines(keepends=True):
            statement+=line
            if sqlite3.complete_statement(statement):
                cursor=c.execute(statement)
                statements.append(dict(sql=statement,rows=[dict(r) for r in cursor.fetchall()]));statement=''
        write_json(E/'sql_examples_results.json',statements)
        dump=logical_hash(c);counts=four.summary(c)
        backups=[]
        for path in [four.BASE/'backups/portrait_four_features_v1.backup.sqlite3',four.BASE/'restored/portrait_four_features_v1.sqlite3']:
            with closing(db.connect(path)) as restored:
                assert logical_hash(restored)==dump and four.summary(restored)==counts
                assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert not restored.execute('PRAGMA foreign_key_check').fetchall()
                rg=four.SqlFourGallery(restored)
                for key in QUERIES:
                    assert four.query(restored,key,top_k=2000,persist=False,gallery=rg)['modes']==four.query(c,key,top_k=2000,persist=False,gallery=sql)['modes']
            backups.append(dict(path=str(path),sha256=db.digest(path),logical_sql_dump_sha256=dump,integrity='ok',full_ranking_parity=True))
    suite=unittest.TestSuite()
    for pattern in ['test_report_v2.py','test_search_ab.py','test_color_features.py','test_color_report_compliance.py',
                    'test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py',
                    'test_c2_root_hog.py','test_c2_pipeline.py','test_fusion_four.py']:
        suite.addTests(unittest.TestLoader().discover(str(four.ROOT/'tests'),pattern=pattern))
    for pattern in ['test_database.py','test_four_feature.py']:
        suite.addTests(unittest.TestLoader().discover(str(four.ROOT/'database/tests'),pattern=pattern))
    with (E/'tests.log').open('x',encoding='utf8') as stream:
        tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    assert tests.wasSuccessful() and not tests.skipped
    baseline=read_json(E/'baseline_before.json')
    changed=[name for name,value in baseline.items() if not Path(name).is_file() or db.digest(name)!=value]
    assert not changed,changed
    write_json(E/'verification.json',dict(status='PASS',date='2026-11-24',timezone='Asia/Saigon',
        counts=counts,source_database_sha256=db.digest(four.SOURCE_DB),database_sha256=db.digest(four.DEFAULT_DB),
        database_path=str(four.DEFAULT_DB),vector_roundtrips=5751,all_vector_bytes_exact=True,
        fourway_calibration_pair_count=20000,fourway_pair_distance_count=80000,all_pair_distances_exact=True,
        medians=params['medians'],epsilon=params['epsilon'],epsilon_c1=params['epsilon_c1'],pair_ids_sha256=params['pair_ids_sha256'],
        authority_sha256=four.AUTHORITY_SHA,policy_sha256=f.POLICY_SHA256,migration_sha256=four.MIGRATION_SHA,
        parity_atol=1e-12,parity_rtol=1e-12,observed_max_abs_error=0.,full_ranking_rows=35900,
        full_rankings_equal=True,queries=queries,top5_rows=125,original_tables_preserved=len(preservation),
        backups=backups,logical_sql_dump_sha256=dump,tests_run=tests.testsRun,tests_skipped=len(tests.skipped),
        tests_failures=len(tests.failures),tests_errors=len(tests.errors),protected_files=len(baseline),changed_files=changed,
        refit_or_extraction_runs=0,new_image_adapter=False,full_anatomical_compliance_claimed=False))
    print('PASS:',tests.testsRun,'tests;',len(baseline),'protected files unchanged;',len(parity),'ranking rows exact')


if __name__=='__main__':main()
