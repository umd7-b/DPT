"""SQLite storage and retrieval; never fits statistics or writes A/B artifacts.

Only sqlite3 and the project's existing NumPy dependency are required. Feature
math, tie breaks, missing-B policy and candidate intersection reuse report v2.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import uuid

import numpy as np

from features.A_geometry.src import report_v2 as a_v2
from features.B_color.src import report_v2 as b_v2
from retrieval import search_ab as legacy
from retrieval import search_ab_v2 as v2
from shared.report_v2 import REPORT, digest, read_csv, read_json, pair_ids_digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'database/data/portrait_ab_v2.sqlite3'
DATASET = Path('D:/TuNam4/dataset_HF_CFD_final')
DATASET_VERSION = 'dataset_HF_CFD_final:immutable_v1'
CALIBRATION_ID = 'AB_report_v2:frozen_pairs_v1'
SCHEMA = Path(__file__).with_name('schema.sql')


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def encode_vector(value, dimension):
    """Contiguous IEEE bytes, explicit endian dtype; no precision conversion."""
    value = np.asarray(value)
    if (value.dtype.str not in ('<f4', '<f8', '>f4', '>f8')
            or value.shape != (dimension,) or not np.isfinite(value).all()):
        raise ValueError('Expected one finite float32/float64 vector of the declared dimension')
    payload = value.tobytes(order='C')
    return payload, value.dtype.str, sha_bytes(payload)


def decode_vector(payload, dtype, dimension, expected_hash):
    if dtype not in ('<f4', '<f8', '>f4', '>f8') or dimension <= 0 or payload is None:
        raise ValueError('Invalid vector metadata')
    if len(payload) != dimension * np.dtype(dtype).itemsize or sha_bytes(payload) != expected_hash:
        raise ValueError('Vector length/hash mismatch')
    value = np.frombuffer(payload, dtype=np.dtype(dtype)).copy()
    if not np.isfinite(value).all():
        raise ValueError('Nonfinite vector in database')
    return value


def connect(path=DEFAULT_DB, *, readonly=True):
    """Open an existing database only; creation belongs to import_v2."""
    path = Path(path).resolve()
    connection = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=5000')
    if connection.execute('PRAGMA user_version').fetchone()[0] != 1:
        connection.close()
        raise ValueError('Unsupported portrait database schema version')
    return connection


def insert_row(connection, table, record):
    # Table and column names below are internal constants, never CLI input.
    columns = ','.join(record)
    connection.execute(f'INSERT INTO {table} ({columns}) VALUES ({",".join("?" for _ in record)})',
                       tuple(record.values()))


def _insert_feature(connection, image_id, version, value, dimension, dtype, ai, fi, provenance, reason=None):
    payload, actual_dtype, checksum = (None, dtype, None) if value is None else encode_vector(value, dimension)
    if actual_dtype != dtype:
        raise ValueError('Feature dtype disagrees with version')
    insert_row(connection, 'FeatureVectors', dict(image_id=image_id, feature_version=version,
        vector_data=payload, dtype=dtype, dimension=dimension, status='missing' if value is None else 'valid',
        missing_reason=reason, vector_sha256=checksum, a_row_index=ai, feature_row_index=fi,
        provenance_json=json_text(provenance)))


def _import_eyes(connection, catalog):
    """Use three saved audit measurements; never invent original preprocessing."""
    folder = ROOT / 'docs/audits/pre_c_evidence'
    evidence_path = folder / 'mapping_verification.json'
    mapping = read_json(evidence_path)
    package = read_json(folder / 'native_mediapipe_topology.json')
    model = ROOT / 'models/face_landmarker.task'
    script = ROOT / 'docs/audits/pre_c_tools/review_mapping.py'
    model_hash = digest(model)
    original = read_json(folder / 'baseline_before.json')
    created = {str((ROOT / r['path']).resolve()):r['sha256']
               for r in read_json(folder / 'created_files_manifest.json')['files']}
    if model_hash != original[str(model.resolve())]:
        raise ValueError('Audit model has changed since measurement')
    for asset in [evidence_path,script,folder / 'native_mediapipe_topology.json']:
        if digest(asset) != created[str(asset.resolve())]:
            raise ValueError('Audit provenance was modified')
    for sample in mapping['samples']:
        image_id = Path(sample['image_name']).stem
        row = catalog[image_id]
        points_path = folder / f'{image_id}_points478.npy'
        if (digest(points_path) != created[str(points_path.resolve())]
                or row['sha256'] != original[str(Path(DATASET/'images'/sample['image_name']).resolve())]):
            raise ValueError('Audit landmarks/image no longer match recorded provenance')
        points = np.load(points_path, allow_pickle=False)
        if points.shape != (478, 2) or not np.isfinite(points).all():
            raise ValueError('Invalid saved audit landmarks')
        # These float64 scalar means are the saved audit oracle measurements,
        # not the float32 extractor mean and not original preprocessing metadata.
        left = points[[33, 160, 158, 133, 153, 144]].astype(np.float64).mean(axis=0)
        right = points[[362, 385, 387, 263, 373, 380]].astype(np.float64).mean(axis=0)
        if not (np.array_equal(left, sample['eye_left_mean6']) and np.array_equal(right, sample['eye_right_mean6'])):
            raise ValueError('Eye measurements disagree with saved audit evidence')
        provenance = dict(measurement_date='2026-11-23', image_sha256=row['sha256'],
            landmarks_path=str(points_path), landmarks_sha256=digest(points_path),
            evidence_path=str(evidence_path), evidence_sha256=digest(evidence_path),
            audit_script_sha256=digest(script), model_path=str(model), model_sha256=model_hash,
            package_version=package['package_version'], original_preprocessing_coordinates=False,
            note='Saved audit scalar-f64 mean of six float32 pixel landmarks; canonical anatomy remains unverified')
        insert_row(connection, 'EyeCoordinates', dict(image_id=image_id,
            method='audit_mean6_eyelid_scalar_f64', model_version=f"MediaPipe/{package['package_version']};task_sha256={model_hash}",
            coordinate_role='audit_remeasurement', left_x=float(left[0]), left_y=float(left[1]),
            right_x=float(right[0]), right_y=float(right[1]),
            coordinate_frame='pixel_xy_top_left; left/right follow viewer/code convention',
            provenance_json=json_text(provenance)))


def import_v2(path=DEFAULT_DB, *, dataset=DATASET, a_directory=a_v2.DEFAULT_OUTPUT,
              b_directory=b_v2.DEFAULT_OUTPUT, calibration_directory=v2.OUT / 'calibration', import_eyes=True):
    """Validate input files; INSERT into a new SQLite DB in one transaction."""
    path, dataset = Path(path).resolve(), Path(dataset).resolve()
    if path.exists():
        raise FileExistsError('Refusing to overwrite an existing database')
    if digest(REPORT) != legacy.REPORT_SHA256:
        raise ValueError('Authoritative PDF hash mismatch')
    a_directory, b_directory = Path(a_directory).resolve(), Path(b_directory).resolve()
    calibration_directory = Path(calibration_directory).resolve()
    gallery = v2.load_gallery(a_directory, b_directory)
    ar, av, _ = a_v2.load_gallery(a_directory)
    br, bv, _, _ = b_v2.load_gallery(b_directory)
    catalog_rows = read_csv(dataset / 'metadata.csv')
    catalog = {r['image_id']: r for r in catalog_rows}
    if len(ar) != 1438 or len(br) != 1437 or len(catalog) != 1438 or len(catalog_rows) != 1438:
        raise ValueError('Expected unchanged 1438-image / 1437-valid-B corpus')
    if {r['image_id'] for r in ar} != set(catalog):
        raise ValueError('Dataset and A image_id sets differ')
    if any(int(r['a_row_index']) != i for i, r in enumerate(ar)):
        raise ValueError('A row index order mismatch')
    params_path = calibration_directory / 'median_params.json'
    pairs_path = calibration_directory / 'representative_pairs.csv'
    params, pairs = read_json(params_path), read_csv(pairs_path)
    if (params['schema_id'] != v2.SCHEMA_ID or params['feature_versions'] != v2.VERSIONS
            or params['fingerprint'] != gallery.fingerprint or params['pairs_sha256'] != digest(pairs_path)
            or params['image_ids'] != [r['image_id'] for r in gallery.rows]
            or params['pair_count'] != len(pairs)
            or params['pair_ids_sha256'] != pair_ids_digest([(r['image_id_1'],r['image_id_2']) for r in pairs])):
        raise ValueError('Wrong-version, stale or corrupt calibration')
    for kind in ('a', 'b'):
        if params['median_'+kind] != float(np.median([float(r['distance_'+kind]) for r in pairs])):
            raise ValueError('Saved median disagrees with pair distances')
    manifest = {r['image_id']:r for r in read_csv(b_directory / 'manifest.csv')}
    if set(manifest) != set(catalog):
        raise ValueError('B manifest must include every image, including missing features')
    ai_by_id = {r['image_id']:i for i,r in enumerate(ar)}
    catalog_positions = {r['image_id']:i for i,r in enumerate(catalog_rows)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb'):
        pass  # Reserve without ever replacing a file from another run.
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript('BEGIN IMMEDIATE;\n' + SCHEMA.read_text(encoding='utf-8'))
        insert_row(connection, 'SchemaInfo', dict(version=1, report_sha256=legacy.REPORT_SHA256,
            created_at=utc_now(), implementation_decisions=json_text(dict(dbms='SQLite local prototype',
                vectors='typed IEEE BLOB per image/version; A/B/C logical groups, C1/C2 separate future vectors',
                scope='A/B only; no full compliance certification'))))
        insert_row(connection, 'DatasetVersions', dict(dataset_version=DATASET_VERSION,
            metadata_sha256=digest(dataset / 'metadata.csv'),
            provenance_json=json_text(dict(path=str(dataset), image_count=1438,
                authority='Local immutable corpus label, not an upstream release claim'))))
        persons = set()
        for row in ar:
            identity = row['image_id']
            source = catalog[identity]
            original_id = source['source_person_id'].strip()
            namespace = source.get('source_dataset') or source['source']
            person_id = f'{namespace}:{original_id}' if original_id else None
            if person_id and person_id not in persons:
                insert_row(connection, 'Persons', dict(person_id=person_id, source_namespace=namespace,
                    source_person_id=original_id, evidence_json=json_text(dict(metadata_path=str(dataset/'metadata.csv'),
                    metadata_sha256=digest(dataset/'metadata.csv'), claim='Source-scoped label; not cross-source identity resolution'))))
                persons.add(person_id)
            image_path = Path(row['image_path']).resolve()
            payload = image_path.read_bytes()
            if sha_bytes(payload) != source['sha256'] or source['filename'] != row['image_name']:
                raise ValueError('Image content/name mismatch: ' + identity)
            if payload[:8] != b'\x89PNG\r\n\x1a\n' or payload[12:16] != b'IHDR':
                raise ValueError('Expected audited PNG source')
            width, height = struct.unpack('>II', payload[16:24])
            insert_row(connection, 'Images', dict(image_id=identity, filename=row['image_name'],
                image_path=str(image_path), source=source['source'], image_hash=source['sha256'],
                width=width, height=height, dataset_version=DATASET_VERSION, person_id=person_id,
                catalog_row_index=catalog_positions[identity], a_row_index=ai_by_id[identity],
                metadata_json=json_text(source)))
        if import_eyes:
            _import_eyes(connection, catalog)
        definitions = [('A', a_directory, av, [('zscore150','normalization_stats.npz')]),
                       ('B', b_directory, bv, [('Lab24','moment_normalization_stats.npz'),('final144','final_normalization_stats.npz')])]
        for kind, directory, vectors, stages in definitions:
            schema_path = directory / 'schema.json'
            schema = read_json(schema_path)
            stats_hashes = [(name,digest(directory/file)) for name,file in stages]
            insert_row(connection, 'FeatureVersions', dict(feature_version=schema['id'], logical_group=kind,
                feature_name=kind, schema_json=json_text(schema), schema_hash=digest(schema_path),
                dimension=vectors.shape[1], dtype=vectors.dtype.str,
                normalization_version=schema['id']+':saved_normalization',
                stats_hash=sha_bytes(json_text(stats_hashes).encode()), status='numeric_v2_verified_anatomy_dataset_limits_remain',
                provenance_json=json_text(dict(directory=str(directory), vector_file_hash=digest(directory/f'features_{kind}_normalized.npy'),
                    fingerprint=gallery.fingerprint))))
            for index, (name, filename) in enumerate(stages, 1):
                stats_path = directory / filename
                insert_row(connection, 'NormalizationStages', dict(feature_version=schema['id'],stage_index=index,
                    stage_name=name, stats_data=stats_path.read_bytes(),stats_sha256=digest(stats_path),source_path=str(stats_path)))
        for index,row in enumerate(ar):
            _insert_feature(connection,row['image_id'],a_v2.SCHEMA_ID,av[index],150,av.dtype.str,index,index,row)
        b_index = {r['image_id']:r for r in br}
        for row in ar:
            identity = row['image_id']
            m = manifest[identity]
            if m['source_sha256'] != catalog[identity]['sha256'] or int(m['a_row_index']) != ai_by_id[identity]:
                raise ValueError('B/A identity/hash mismatch')
            valid = identity in b_index
            bi = int(b_index[identity]['feature_row_index']) if valid else None
            _insert_feature(connection,identity,b_v2.SCHEMA_ID,bv[bi] if valid else None,144,bv.dtype.str,
                ai_by_id[identity],bi,m,reason=None if valid else m['reason'])
        insert_row(connection,'Calibrations',dict(calibration_id=CALIBRATION_ID,schema_version=params['schema_id'],
            epsilon=params['epsilon'],pair_count=len(pairs),pair_ids_sha256=params['pair_ids_sha256'],
            params_data=params_path.read_bytes(),params_sha256=digest(params_path),pairs_csv_data=pairs_path.read_bytes(),
            pairs_csv_sha256=digest(pairs_path),fingerprint_json=json_text(params['fingerprint']),experiment=v2.EXPERIMENT))
        for kind,version in [('a',a_v2.SCHEMA_ID),('b',b_v2.SCHEMA_ID)]:
            insert_row(connection,'CalibrationComponents',dict(calibration_id=CALIBRATION_ID,
                feature_version=version,median=params['median_'+kind]))
        connection.executemany('INSERT INTO CalibrationCandidates VALUES (?,?,?)',
            [(CALIBRATION_ID,i,key) for i,key in enumerate(params['image_ids'])])
        connection.executemany('INSERT INTO CalibrationPairs VALUES (?,?,?,?)',
            [(CALIBRATION_ID,i,r['image_id_1'],r['image_id_2']) for i,r in enumerate(pairs)])
        connection.executemany('INSERT INTO CalibrationPairDistances VALUES (?,?,?,?)',
            [(CALIBRATION_ID,i,version,float(r['distance_'+kind])) for i,r in enumerate(pairs)
             for kind,version in [('a',a_v2.SCHEMA_ID),('b',b_v2.SCHEMA_ID)]])
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign-key validation failed')
        connection.commit()
        return counts(connection)
    except BaseException:
        connection.rollback()
        connection.close()
        path.unlink()  # Only the new file reserved by this function, never input artifacts.
        raise
    finally:
        connection.close()


def counts(connection):
    tables = ['Images','Persons','EyeCoordinates','FeatureVersions','FeatureVectors','NormalizationStages',
              'CalibrationPairs','CalibrationPairDistances','RetrievalRuns','RetrievalResults']
    result = {name:connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in tables}
    result['valid_A'] = connection.execute("SELECT count(*) FROM ImageFeatureStatus WHERE feature_name='A' AND status='valid'").fetchone()[0]
    result['valid_B'] = connection.execute("SELECT count(*) FROM ImageFeatureStatus WHERE feature_name='B' AND status='valid'").fetchone()[0]
    return result


def get_image(connection, image_id):
    row = connection.execute('SELECT * FROM Images WHERE image_id=?',(image_id,)).fetchone()
    if row is None:
        raise KeyError('Unknown image_id: '+image_id)
    return dict(row)


def get_vector(connection, image_id, version):
    row = connection.execute('SELECT * FROM FeatureVectors WHERE image_id=? AND feature_version=?',(image_id,version)).fetchone()
    if row is None:
        raise KeyError('Missing feature record')
    if row['status'] == 'missing':
        if row['vector_data'] is not None or not row['missing_reason']:
            raise ValueError('Invalid missing-feature record')
        return None
    return decode_vector(row['vector_data'],row['dtype'],row['dimension'],row['vector_sha256'])


def load_stats(connection, version):
    rows = connection.execute('SELECT * FROM NormalizationStages WHERE feature_version=? ORDER BY stage_index',(version,)).fetchall()
    if not rows:
        raise ValueError('Missing normalization stages')
    version_row = connection.execute('SELECT stats_hash FROM FeatureVersions WHERE feature_version=?',(version,)).fetchone()
    hashes = [(r['stage_name'],r['stats_sha256']) for r in rows]
    if sha_bytes(json_text(hashes).encode()) != version_row['stats_hash']:
        raise ValueError('Normalization stage contract mismatch')
    result = []
    for row in rows:
        if sha_bytes(row['stats_data']) != row['stats_sha256']:
            raise ValueError('Normalization BLOB hash mismatch')
        with np.load(io.BytesIO(row['stats_data']),allow_pickle=False) as saved:
            result.append({key:saved[key].copy() for key in saved.files})
    return result


def load_calibration(connection, calibration_id=CALIBRATION_ID):
    row = connection.execute('SELECT * FROM Calibrations WHERE calibration_id=?',(calibration_id,)).fetchone()
    if row is None or sha_bytes(row['params_data']) != row['params_sha256'] or sha_bytes(row['pairs_csv_data']) != row['pairs_csv_sha256']:
        raise ValueError('Calibration BLOB integrity mismatch')
    params = json.loads(row['params_data'])
    if (params['epsilon'] != row['epsilon'] or params['pair_count'] != row['pair_count']
            or params['pair_ids_sha256'] != row['pair_ids_sha256'] or params['fingerprint'] != json.loads(row['fingerprint_json'])):
        raise ValueError('Calibration metadata mismatch')
    components = connection.execute('SELECT feature_version,median FROM CalibrationComponents WHERE calibration_id=?',(calibration_id,)).fetchall()
    if {r['feature_version']:r['median'] for r in components} != {
            params['feature_versions'][k]:params['median_'+k] for k in ('a','b')}:
        raise ValueError('Calibration feature version/median mismatch')
    pairs = connection.execute('SELECT image_id_1,image_id_2 FROM CalibrationPairs WHERE calibration_id=? ORDER BY pair_index',(calibration_id,)).fetchall()
    if len(pairs) != row['pair_count'] or pair_ids_digest([tuple(r) for r in pairs]) != row['pair_ids_sha256']:
        raise ValueError('Calibration ordered pair IDs mismatch')
    return params


def load_gallery(connection, calibration_id=CALIBRATION_ID):
    """Load all vectors/metadata from SQL only, with explicit identity joins."""
    params = load_calibration(connection,calibration_id)
    va,vb = params['feature_versions']['a'],params['feature_versions']['b']
    # Validate that saved normalization parameters survive without external files.
    load_stats(connection,va); load_stats(connection,vb)
    rows = connection.execute('''SELECT i.*, a.vector_data AS av, a.vector_sha256 AS ah,
        a.dtype AS ad, a.dimension AS an, b.vector_data AS bv, b.vector_sha256 AS bh,
        b.dtype AS bd, b.dimension AS bn, b.provenance_json AS bmeta
        FROM CalibrationCandidates c JOIN Images i ON i.image_id=c.image_id
        JOIN FeatureVectors a ON a.image_id=i.image_id AND a.feature_version=? AND a.status='valid'
        JOIN FeatureVectors b ON b.image_id=i.image_id AND b.feature_version=? AND b.status='valid'
        WHERE c.calibration_id=? ORDER BY c.candidate_index''',(va,vb,calibration_id)).fetchall()
    if [r['image_id'] for r in rows] != params['image_ids']:
        raise ValueError('Calibrated candidate set/order mismatch')
    images = connection.execute('SELECT * FROM Images ORDER BY a_row_index').fetchall()
    a_rows = [dict(json.loads(r['metadata_json']),image_id=r['image_id'],image_name=r['filename'],
        image_path=r['image_path'],a_row_index=r['a_row_index']) for r in images]
    all_a = np.stack([get_vector(connection,r['image_id'],va) for r in images])
    common_rows = [dict(json.loads(r['bmeta']),image_id=r['image_id']) for r in rows]
    missing = [dict(image_id=r['image_id'],image_name=r['filename'],image_path=r['image_path'],
        a_row_index=r['a_row_index'],reason=r['missing_reason']) for r in connection.execute('''
        SELECT i.*,v.missing_reason FROM Images i JOIN FeatureVectors v USING(image_id)
        WHERE v.feature_version=? AND v.status='missing' ORDER BY i.a_row_index''',(vb,))]
    return legacy.Gallery(common_rows,
        np.stack([decode_vector(r['av'],r['ad'],r['an'],r['ah']) for r in rows]),
        np.stack([decode_vector(r['bv'],r['bd'],r['bn'],r['bh']) for r in rows]),
        a_rows,all_a,missing,params['fingerprint'])


def _resolve_query(connection, image):
    value = str(image)
    known = connection.execute('SELECT * FROM Images WHERE image_id=? OR filename=?',(value,value)).fetchall()
    path = Path(image)
    if not path.is_file():
        if len(known) != 1:
            raise FileNotFoundError('Unknown image path/name/id: '+value)
        path = Path(known[0]['image_path'])
    path = path.resolve()
    checksum = digest(path)
    ids = {r['image_id'] for r in connection.execute('SELECT image_id FROM Images WHERE image_hash=?',(checksum,))}
    return path,checksum,ids


def search(connection, image, *, mode='all', top_k=5, weight_a=.5, weight_b=.5,
           calibration_id=CALIBRATION_ID, persist=True):
    """SQL-loaded gallery; unchanged NumPy Euclid/median/rank algorithm.

    External images use the existing separate-environment v2 workers, whose
    statistics hashes must match the exact NPZ BLOBs stored in this database.
    """
    if mode not in ('all','A','B','AB'):
        raise ValueError('mode must be all, A, B or AB')
    legacy.validate_weights(weight_a,weight_b)
    if top_k <= 0:
        raise ValueError('top_k must be positive')
    gallery = load_gallery(connection,calibration_id)
    params = load_calibration(connection,calibration_id)
    path,checksum,excluded = _resolve_query(connection,image)
    va,vb = params['feature_versions']['a'],params['feature_versions']['b']
    reason = None
    if excluded:
        identity = min(excluded)
        qa,qb = get_vector(connection,identity,va),get_vector(connection,identity,vb)
        if qb is None:
            reason = connection.execute('SELECT missing_reason FROM FeatureVectors WHERE image_id=? AND feature_version=?',(identity,vb)).fetchone()[0]
        info = dict(source='sqlite_normalized_v2',query_refit=False)
    else:
        with tempfile.TemporaryDirectory(prefix='portrait_sqlite_query_') as tmp:
            destination = Path(tmp)
            a = v2.run_worker('a',path,destination,a_v2.DEFAULT_OUTPUT)
            b = v2.run_worker('b',path,destination,b_v2.DEFAULT_OUTPUT)
            expected = {r['stage_name']:r['stats_sha256'] for r in connection.execute('SELECT stage_name,stats_sha256 FROM NormalizationStages WHERE feature_version IN (?,?)',(va,vb))}
            if (a['stats_sha256'] != expected['zscore150'] or b['moment_stats_sha256'] != expected['Lab24']
                    or b['final_stats_sha256'] != expected['final144']):
                raise ValueError('Worker statistics differ from database')
            qa = np.load(destination/'query_A_normalized.npy',allow_pickle=False)
            qb = np.load(destination/'query_B_normalized.npy',allow_pickle=False) if b['status']=='valid' else None
            reason = None if qb is not None else json_text(b)
            info = dict(source='unchanged_v2_workers',a=a,b=b,query_refit=False)
    if digest(path) != checksum:
        raise ValueError('Query content changed during search')
    result = legacy.rankings(gallery,qa,qb,params,weight_a,weight_b,top_k,excluded)
    selected = {'A':'a_only','B':'b_only','AB':'ab'}
    runs = {}
    # Each mode is an independent, traceable run, committed atomically together.
    with connection:
        for run_mode,key in selected.items():
            if mode not in ('all',run_mode):
                continue
            run_id = str(uuid.uuid4())
            rows = result[key]
            status = 'missing_B' if qb is None else 'valid'
            if persist:
                insert_row(connection,'RetrievalRuns',dict(run_id=run_id,created_at=utc_now(),
                    query_image_id=min(excluded) if excluded else None,query_path=str(path),query_hash=checksum,
                    mode=run_mode,weight_a=weight_a,weight_b=weight_b,calibration_id=calibration_id,
                    feature_version_a=va,feature_version_b=vb,top_k=top_k,status=status,missing_reason=reason,
                    excluded_ids_json=json_text(sorted(excluded)),provenance_json=json_text(info)))
                for version,value,dimension in [(va,qa,150),(vb,qb,144)]:
                    payload,dtype,h = (None,'<f8',None) if value is None else encode_vector(value,dimension)
                    insert_row(connection,'QueryVectors',dict(run_id=run_id,feature_version=version,
                        vector_data=payload,dtype=dtype,dimension=dimension,vector_sha256=h,
                        status='missing' if value is None else 'valid',missing_reason=reason if value is None else None))
                for r in rows:
                    insert_row(connection,'RetrievalResults',dict(run_id=run_id,rank=r['rank'],image_id=r['image_id'],
                        dA=r['distance_a'],dB=r['distance_b'],normalized_a=r['normalized_a'],normalized_b=r['normalized_b'],
                        D_AB=r['distance_total'],score=r['score']))
            runs[run_mode] = dict(run_id=run_id if persist else None,status=status,results=rows)
    return dict(query=str(path),query_sha256=checksum,excluded_self_ids=sorted(excluded),
                experiment=v2.EXPERIMENT,query_info=info,runs=runs)


def backup(source, destination):
    """SQLite online backup; destination must be new, including restore copies."""
    source,destination = Path(source).resolve(),Path(destination).resolve()
    if source == destination:
        raise ValueError('Backup source and destination must differ')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb'):
        pass
    try:
        with closing(connect(source)) as original, closing(sqlite3.connect(destination)) as target:
            original.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup integrity failure')
    except BaseException:
        destination.unlink()
        raise
    return dict(source=str(source),destination=str(destination),sha256=digest(destination))
