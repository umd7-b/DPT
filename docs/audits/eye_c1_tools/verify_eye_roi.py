"""Read-only comparison of accepted data plus new DB backup/restore evidence."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import prepare_eye_roi as task
from shared.report_v2 import read_json,read_csv,write_json,save_csv

E=task.E
ROOT=task.ROOT
BACKUP=ROOT/'database/backups/portrait_ab_v2_eye_metadata_v1.backup.sqlite3'
RESTORE=ROOT/'database/restored/portrait_ab_v2_eye_metadata_v1.sqlite3'


def table_hash(c,name):
    # Table names are sqlite_master values, never shell or user text.
    h=hashlib.sha256()
    for row in c.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid'):
        h.update(repr(tuple(row)).encode('utf-8')); h.update(b'\n')
    return h.hexdigest()


def dump_hash(c):
    h=hashlib.sha256()
    for line in c.iterdump():
        h.update(line.encode('utf-8')); h.update(b'\n')
    return h.hexdigest()


def main():
    if BACKUP.exists() or RESTORE.exists():
        raise FileExistsError('Eye metadata snapshots already exist; refusing overwrite')
    names,points,images,logs,proof=task.load_archive()
    groups,_=task.source_groups()
    baseline=read_json(E/'baseline_before.json')
    assert not [p for p,h in baseline.items() if task.db.digest(p)!=h]
    checks=[]; original_tables=[]; comparisons=[]
    a_meta={r['image_id']:float(r['eye_distance']) for r in read_csv(task.db.a_v2.DEFAULT_OUTPUT/'metadata.csv')}
    with closing(task.db.connect()) as original,closing(task.db.connect(task.NEW_DB)) as new:
        assert new.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not new.execute('PRAGMA foreign_key_check').fetchall()
        rows=new.execute('SELECT * FROM EyeMetadataAuditV1 ORDER BY archive_row_index').fetchall()
        assert len(rows)==1438
        for row in rows:
            i=row['archive_row_index']; name=names[i]; image=images[name]; p=points[i]
            coords=task.measure_eyes(p,image['width'],image['height'],groups)
            actual=tuple(row[k] for k in ('left_x','left_y','right_x','right_y'))
            assert actual==coords and row['image_id']==image['image_id']
            assert row['source_landmark_hash']==task.db.sha_bytes(p.tobytes(order='C'))
            provenance=json.loads(row['provenance'])
            assert provenance['archive_sha256']==proof['archive_sha256']
            assert provenance['image_sha256']==image['image_hash']
            assert row['measurement_role']=='audit_remeasurement'
            scalar=tuple(math.fsum(float(p[k,j]) for k in indices)/6
                for indices in [groups['LEFT_EYE'],groups['RIGHT_EYE']] for j in (0,1))
            err=max(abs(a-b) for a,b in zip(coords,scalar))
            # Bound the float32 reduction rounding; do not replace the stored method.
            assert err<3e-5
            current_ipd=float(np.linalg.norm(np.array(coords[:2],np.float32)-np.array(coords[2:],np.float32)))
            checks.append(dict(image_id=image['image_id'],archive_row_index=i,source_landmark_hash=row['source_landmark_hash'],
                left_x=actual[0],left_y=actual[1],right_x=actual[2],right_y=actual[3],sqlite_roundtrip_exact=True,
                max_abs_difference_from_scalar_float64_mean=err,remeasured_ipd=current_ipd,
                a_metadata_ipd=a_meta[row['image_id']],abs_ipd_difference_from_a_metadata=abs(current_ipd-a_meta[row['image_id']])))
        attempts=[dict(r) for r in new.execute('SELECT status,count(*) AS count FROM EyeMeasurementAttempts GROUP BY status')]
        assert attempts==[dict(status='measured',count=1438)]
        # All old tables must be identical; only additive eye records are allowed.
        for row in original.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            name=row['name']
            if name=='EyeCoordinates':
                old_rows=original.execute('SELECT * FROM EyeCoordinates').fetchall()
                for old in old_rows:
                    actual=new.execute('SELECT * FROM EyeCoordinates WHERE image_id=? AND method=? AND model_version=? AND coordinate_role=?',
                        tuple(old[k] for k in ('image_id','method','model_version','coordinate_role'))).fetchone()
                    assert tuple(actual)==tuple(old)
                original_tables.append(dict(table=name,original_rows_preserved=len(old_rows),new_total=1441))
            else:
                before,after=table_hash(original,name),table_hash(new,name)
                assert before==after,name
                original_tables.append(dict(table=name,all_rows_and_values_identical=True,sha256=before))
        assert new.execute("SELECT count(*) FROM FeatureVersions WHERE logical_group='C'").fetchone()[0]==0
        old_g,new_g=task.db.load_gallery(original),task.db.load_gallery(new)
        assert old_g.a.tobytes()==new_g.a.tobytes() and old_g.b.tobytes()==new_g.b.tobytes()
        params=task.db.load_calibration(new)
        for key in ['cfd_final_00001','cfd_final_00088','cfd_final_00144','hf_merged_00209','new_query']:
            expected=read_json(task.db.v2.OUT/'queries'/key/'results.json')
            if key=='new_query':
                # Reuse a previously persisted query vector; NO new detector/worker.
                run=original.execute("SELECT run_id FROM RetrievalRuns WHERE mode='AB' AND query_hash=? LIMIT 1",
                    (expected['query_info']['source_sha256'],)).fetchone()
                q={}
                for row in original.execute('SELECT * FROM QueryVectors WHERE run_id=?',(run['run_id'],)):
                    q[row['feature_version']]=task.db.decode_vector(row['vector_data'],row['dtype'],row['dimension'],row['vector_sha256'])
                qa,qb=q[params['feature_versions']['a']],q[params['feature_versions']['b']]
            else:
                qa=task.db.get_vector(original,key,params['feature_versions']['a'])
                qb=task.db.get_vector(original,key,params['feature_versions']['b'])
            before=task.db.legacy.rankings(old_g,qa,qb,params,.5,.5,1438,expected['excluded_self_ids'])
            after=task.db.legacy.rankings(new_g,qa,qb,params,.5,.5,1438,expected['excluded_self_ids'])
            assert before==after
            for mode,rows in after.items():
                assert rows[:5]==expected['results'][mode]
                comparisons.append(dict(query=key,mode=mode,full_rank_count=len(rows),
                    full_rank_ids_and_distances_exactly_equal=True,top5_equal_to_frozen_file=True,
                    top5_image_ids=[r['image_id'] for r in rows[:5]]))
        current_dump=dump_hash(new)
        total_eye_rows=new.execute('SELECT count(*) FROM EyeCoordinates').fetchone()[0]
    save_csv(E/'eye_roundtrip_validation.csv',checks)
    write_json(E/'original_database_tables_validation.json',original_tables)
    write_json(E/'ranking_preservation.json',comparisons)
    # Retain details about the three historical scalar-f64 measurements.
    with closing(task.db.connect(task.NEW_DB)) as c:
        delta=[]
        for row in c.execute("""SELECT old.image_id,old.left_x AS lx0,old.left_y AS ly0,old.right_x AS rx0,old.right_y AS ry0,
            n.left_x,n.left_y,n.right_x,n.right_y FROM EyeCoordinates old JOIN EyeMetadataAuditV1 n USING(image_id)
            WHERE old.method='audit_mean6_eyelid_scalar_f64'"""):
            old=[row[k] for k in ('lx0','ly0','rx0','ry0')]; new=[row[k] for k in ('left_x','left_y','right_x','right_y')]
            delta.append(dict(image_id=row['image_id'],historical_scalar64=old,new_numpy32=new,
                max_abs_difference=max(abs(a-b) for a,b in zip(old,new)),old_record_preserved=True))
        write_json(E/'historical_eye_measurement_comparison.json',delta)
    backup=task.db.backup(task.NEW_DB,BACKUP)
    restore=task.db.backup(BACKUP,RESTORE)
    with closing(task.db.connect(RESTORE)) as c:
        assert dump_hash(c)==current_dump
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        restored=[tuple(r) for r in c.execute('SELECT * FROM EyeMetadataAuditV1 ORDER BY archive_row_index')]
    with closing(task.db.connect(task.NEW_DB)) as c:
        assert restored==[tuple(r) for r in c.execute('SELECT * FROM EyeMetadataAuditV1 ORDER BY archive_row_index')]
    write_json(E/'backup_restore.json',dict(backup=backup,restore=restore,
        full_database_sql_dump_sha256=current_dump,all_tables_and_eye_metadata_equal=True,
        integrity_check='ok',foreign_key_errors=[]))
    pages=read_json(ROOT/'docs/audits/evidence/pdf_pages.json')
    write_json(E/'pdf_sections_review.json',dict(pdf_sha256=task.db.digest(task.db.REPORT),
        text_source='Previously extracted audit text; source PDF hash remains authenticated',
        cached_text_sha256=task.db.digest(ROOT/'docs/audits/evidence/pdf_pages.json'),
        pages=[dict(physical_page=i+1,text=pages[i]) for i in [4,7,8,12,13,14]]))
    changed=[p for p,h in baseline.items() if task.db.digest(p)!=h]
    assert not changed,changed
    previews=read_json(E/'roi_preview_validation.json')
    assert 'mediapipe' not in sys.modules
    result=dict(status='PASS',measured_images=len(checks),unmeasurable_images=0,
        inherited_historical_eye_rows=3,new_eye_rows=1438,total_versioned_eye_rows=total_eye_rows,
        sqlite_roundtrip_exact=True,source_landmark_hashes_exact=True,
        max_abs_delta_vs_scalar64_mean=max(r['max_abs_difference_from_scalar_float64_mean'] for r in checks),
        max_ipd_delta_vs_a_metadata=max(r['abs_ipd_difference_from_a_metadata'] for r in checks),
        original_tables_verified=len(original_tables),source_database_unchanged=True,
        source_landmark_archive_unchanged=True,source_database_sha256=task.db.digest(task.db.DEFAULT_DB),
        new_database=str(task.NEW_DB),new_database_sha256=task.db.digest(task.NEW_DB),
        backup_restore_verified=True,full_ranking_cases=len(comparisons),
        full_rank_ids_and_distances_unchanged=True,overlay_cases=len(previews['cases']),
        draft_polygons=4,anatomical_roi_approved=False,reran_mediapipe=False,
        c1_c2_vectors_created=False,protected_files_checked=len(baseline),changed_existing_files=changed,
        original_preprocessing_coordinates_verified=False,full_system_compliance=False)
    write_json(E/'verification_summary.json',result)
    print(task.db.json_text(result))


if __name__=='__main__':
    main()
