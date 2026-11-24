"""Additive SQLite import and gallery-only four-feature retrieval; no feature fitting."""
from contextlib import closing
import argparse
import csv
import io
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

import numpy as np

from database import store as db
from retrieval import fusion_four as fusion
from shared.report_v2 import read_csv, read_json, write_json, pair_ids_digest

ROOT=db.ROOT
BASE=ROOT/'database/four_feature_v1'
DEFAULT_DB=BASE/'data/portrait_four_features_v1.sqlite3'
SOURCE_DB=ROOT/'database/data/portrait_ab_v2_eye_metadata_v1.sqlite3'
MIGRATION=ROOT/'database/migrations/001_four_features_v1.sql'
MIGRATION_SHA='f48ee1916f66aebc7f91b8d3ce4a479d2d08091173f0306bcf6fa62eeff3fba2'
AUTHORITY=BASE/'evidence/authority.json'
AUTHORITY_SHA='ea0b144ac265b33a130b16ecf7ac3ef110283616bcfcac8a7da621049261dfea'
EXTENSION='FOUR_FEATURE_SQLITE_v1'
CALIBRATION_ID='FUSION_AB_C1_C2_v1:frozen_AB_v2_pairs'
MODES=(*fusion.KINDS,'fusion')


def record_hash(record):return db.sha_bytes(db.json_text(dict(record)).encode('utf8'))


def authority():
    if db.digest(AUTHORITY)!=AUTHORITY_SHA:raise ValueError('SQLite import authority hash mismatch')
    return read_json(AUTHORITY)


def summary(c):
    result={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
        ['Images','EyeCoordinates','EyeCoordinateSources','FeatureVersions','FeatureVectors','Calibrations',
         'CalibrationPairs','CalibrationPairDistances','FourFeatureRuns','FourFeatureResults']}
    result['coverage']=[dict(r) for r in c.execute('SELECT * FROM FourFeatureCoverage ORDER BY feature_name,status')]
    return result


def import_database(destination=DEFAULT_DB):
    """Online backup of authenticated source, then one additive SQL transaction."""
    destination=Path(destination).resolve()
    if destination.exists():raise FileExistsError('Destination exists; never overwrite an accepted database')
    auth=authority();fusion.verify_inputs(auth['fingerprint'])
    if db.digest(MIGRATION)!=MIGRATION_SHA:raise ValueError('Migration hash mismatch')
    gallery=fusion.FourGallery();params=fusion.load_calibration(gallery)
    if params['medians']!=auth['expected_medians']:raise ValueError('Accepted medians changed')
    if db.digest(SOURCE_DB)!=auth['source_database_sha256']:raise ValueError('Source database hash mismatch')
    # Verify every existing A/B value and all image identities before copying.
    with closing(db.connect(SOURCE_DB)) as source:
        images={r['image_id']:dict(r) for r in source.execute('SELECT * FROM Images')}
        if set(images)!=set(gallery.by_id):raise ValueError('Database and gallery images differ')
        if source.execute('SELECT count(DISTINCT image_id) FROM EyeMetadataAuditV1').fetchone()[0]!=1438:
            raise ValueError('Source database lacks completed audit eye metadata')
        for kind in ('a','b'):
            version=params['feature_versions'][kind]
            for key,(index,row) in gallery.maps[kind].items():
                stored=source.execute('SELECT * FROM FeatureVectors WHERE image_id=? AND feature_version=?',(key,version)).fetchone()
                expected=gallery.sources[kind][1][index]
                if (stored is None or db.get_vector(source,key,version).tobytes()!=expected.tobytes()
                        or stored['feature_row_index']!=index or images[key]['image_hash']!=gallery.by_id[key]['image_sha256']):
                    raise ValueError('Existing A/B bytes or mapping differ: '+key)
        if db.load_calibration(source)!=read_json(fusion.AB_CALIBRATION/'median_params.json'):
            raise ValueError('Historical AB calibration differs')
    db.backup(SOURCE_DB,destination)
    with closing(db.connect(destination,readonly=False)) as c:
        try:
            c.executescript('BEGIN IMMEDIATE;\n'+MIGRATION.read_text('utf8'))
            db.insert_row(c,'FourFeatureMigrations',dict(extension_version=EXTENSION,migration_sha256=MIGRATION_SHA,
                source_database_sha256=auth['source_database_sha256'],authority_data=AUTHORITY.read_bytes(),
                authority_sha256=AUTHORITY_SHA,policy_data=fusion.POLICY_PATH.read_bytes(),
                policy_sha256=fusion.POLICY_SHA256,created_at=db.utc_now()))
            for kind,source_gallery in [('c1',gallery.c1),('c2',gallery.c2)]:
                version=params['feature_versions'][kind];folder=source_gallery.directory
                schema=read_json(folder/'feature_schema.json')
                # C1/C2 have no fitted gallery stats; hash their existing normalization definition.
                definition=dict(normalization=schema['normalization'],feature_version=version,
                                schema_sha256=db.digest(folder/'feature_schema.json'))
                db.insert_row(c,'FeatureVersions',dict(feature_version=version,logical_group='C',feature_name=kind.upper(),
                    schema_json=db.json_text(schema),schema_hash=db.digest(folder/'feature_schema.json'),
                    dimension=fusion.DIMENSIONS[kind],dtype=source_gallery.matrix.dtype.str,
                    normalization_version=version+':existing_spec_no_fitted_stats',stats_hash=record_hash(definition),
                    status='numeric_verified_anatomy_provisional',provenance_json=db.json_text(dict(
                        source_directory=str(folder),manifest_sha256=db.digest(folder/'manifest.json'),
                        vector_file_sha256=db.digest(folder/('features_'+kind.upper()+'.npy')),
                        normalization_definition=definition,refit=False,anatomical_approval_claimed=False))))
                for name in ['feature_schema.json','manifest.json','feature_rows.csv','extraction_status.csv']:
                    p=folder/name
                    db.insert_row(c,'FourFeatureArtifacts',dict(feature_version=version,artifact_name=name,
                        artifact_data=p.read_bytes(),artifact_sha256=db.digest(p),source_path=str(p)))
                for key,(index,row) in gallery.maps[kind].items():
                    db._insert_feature(c,key,version,source_gallery.matrix[index],fusion.DIMENSIONS[kind],'<f8',
                        images[key]['a_row_index'],index,dict(source_row=row,
                            feature_schema_sha256=db.digest(folder/'feature_schema.json'),
                            source_image_sha256=images[key]['image_hash'],import_extension=EXTENSION))
            for kind in fusion.KINDS:
                version=params['feature_versions'][kind]
                version_row=c.execute('SELECT * FROM FeatureVersions WHERE feature_version=?',(version,)).fetchone()
                folder={'a':db.a_v2.DEFAULT_OUTPUT,'b':db.b_v2.DEFAULT_OUTPUT,
                        'c1':gallery.c1.directory,'c2':gallery.c2.directory}[kind]
                filename='features_'+kind.upper()+('_normalized.npy' if kind in ('a','b') else '.npy')
                db.insert_row(c,'FourFeatureVersionLocks',dict(kind=kind,feature_version=version,
                    version_record_sha256=record_hash(version_row),vector_artifact_sha256=db.digest(folder/filename)))
                c.executemany('INSERT INTO FourFeatureVectorBindings VALUES (?,?,?,?,?)',[
                    (key,version,index,db.sha_bytes(gallery.sources[kind][1][index].tobytes()),gallery.by_id[key]['image_sha256'])
                    for key,(index,row) in gallery.maps[kind].items()])
            folder=fusion.OUT/'calibration'
            db.insert_row(c,'Calibrations',dict(calibration_id=CALIBRATION_ID,schema_version=params['schema_id'],
                epsilon=params['epsilon'],pair_count=params['pair_count'],pair_ids_sha256=params['pair_ids_sha256'],
                params_data=(folder/'median_params.json').read_bytes(),params_sha256=db.digest(folder/'median_params.json'),
                pairs_csv_data=(folder/'representative_pairs.csv').read_bytes(),pairs_csv_sha256=db.digest(folder/'representative_pairs.csv'),
                fingerprint_json=db.json_text(params['fingerprint']),experiment='EXPERIMENTAL_EQUAL_WEIGHTS; four vectors; anatomy provisional'))
            db.insert_row(c,'FourFeatureCalibrations',dict(calibration_id=CALIBRATION_ID,policy_sha256=fusion.POLICY_SHA256,
                epsilon_c1=params['epsilon_c1'],params_sha256=db.digest(folder/'median_params.json'),
                pairs_sha256=db.digest(folder/'representative_pairs.csv'),feature_versions_json=db.json_text(params['feature_versions']),
                configuration='EXPERIMENTAL_EQUAL_WEIGHTS'))
            c.executemany('INSERT INTO CalibrationComponents VALUES (?,?,?)',[
                (CALIBRATION_ID,params['feature_versions'][kind],params['medians'][kind]) for kind in fusion.KINDS])
            c.executemany('INSERT INTO CalibrationCandidates VALUES (?,?,?)',[(CALIBRATION_ID,i,key) for i,key in enumerate(params['image_ids'])])
            pairs=read_csv(folder/'representative_pairs.csv')
            c.executemany('INSERT INTO CalibrationPairs VALUES (?,?,?,?)',[
                (CALIBRATION_ID,int(r['pair_id']),r['image_id_1'],r['image_id_2']) for r in pairs])
            c.executemany('INSERT INTO CalibrationPairDistances VALUES (?,?,?,?)',[
                (CALIBRATION_ID,int(r['pair_id']),params['feature_versions'][kind],float(r['distance_'+kind]))
                for r in pairs for kind in fusion.KINDS])
            if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Foreign key validation failed')
            c.commit()
        except BaseException:
            c.rollback();raise
        SqlFourGallery(c)  # SELECT/bytes/version checks on the actual imported database.
        result=summary(c)
    if db.digest(SOURCE_DB)!=auth['source_database_sha256']:raise ValueError('Source database changed')
    return result


def load_calibration(c,auth,policy,calibration_id=CALIBRATION_ID):
    if calibration_id!=CALIBRATION_ID:raise ValueError('Four-way calibration version isolation: AB or unknown ID refused')
    row=c.execute('SELECT * FROM Calibrations WHERE calibration_id=?',(calibration_id,)).fetchone()
    ext=c.execute('SELECT * FROM FourFeatureCalibrations WHERE calibration_id=?',(calibration_id,)).fetchone()
    folder=fusion.OUT/'calibration'
    if row is None or ext is None:raise ValueError('Four-way calibration unavailable')
    for field,file,hash_field in [('params_data','median_params.json','params_sha256'),
                                  ('pairs_csv_data','representative_pairs.csv','pairs_csv_sha256')]:
        expected=auth['fingerprint'][str(folder/file)]
        if row[hash_field]!=expected or db.sha_bytes(row[field])!=expected:
            raise ValueError('Calibration BLOB/source hash mismatch')
    params=json.loads(row['params_data'])
    if (params['schema_id']!=fusion.SCHEMA_ID or row['schema_version']!=fusion.SCHEMA_ID
            or params['policy_sha256']!=fusion.POLICY_SHA256 or ext['policy_sha256']!=fusion.POLICY_SHA256
            or params['feature_versions']!=policy['feature_versions'] or json.loads(ext['feature_versions_json'])!=params['feature_versions']
            or params['medians']!=auth['expected_medians'] or params['fingerprint']!=policy['input_files']
            or json.loads(row['fingerprint_json'])!=params['fingerprint']
            or row['epsilon']!=params['epsilon'] or params['epsilon']!=fusion.EPSILON
            or ext['epsilon_c1']!=fusion.EPSILON_C1 or params['epsilon_c1']!=fusion.EPSILON_C1
            or ext['params_sha256']!=row['params_sha256'] or ext['pairs_sha256']!=row['pairs_csv_sha256']):
        raise ValueError('Calibration schema/feature/median/epsilon mismatch')
    components={r['feature_version']:r['median'] for r in c.execute('SELECT * FROM CalibrationComponents WHERE calibration_id=?',(calibration_id,))}
    if components!={params['feature_versions'][k]:params['medians'][k] for k in fusion.KINDS}:
        raise ValueError('Calibration component version/median mismatch')
    candidates=[r['image_id'] for r in c.execute('SELECT * FROM CalibrationCandidates WHERE calibration_id=? ORDER BY candidate_index',(calibration_id,))]
    if candidates!=params['image_ids']:raise ValueError('Calibration candidate ID/index mismatch')
    csv_pairs=list(csv.DictReader(io.StringIO(bytes(row['pairs_csv_data']).decode('utf-8-sig'))))
    actual=list(c.execute('SELECT * FROM CalibrationPairs WHERE calibration_id=? ORDER BY pair_index',(calibration_id,)))
    identities=[(r['image_id_1'],r['image_id_2']) for r in actual]
    if (len(actual)!=20000 or row['pair_count']!=20000 or pair_ids_digest(identities)!=params['pair_ids_sha256']
            or row['pair_ids_sha256']!=policy['pair_ids_sha256'] or len(csv_pairs)!=20000
            or any((r['pair_index'],r['image_id_1'],r['image_id_2'])!=(int(s['pair_id']),s['image_id_1'],s['image_id_2'])
                   for r,s in zip(actual,csv_pairs,strict=True))):raise ValueError('Calibration pair identities mismatch')
    distances=list(c.execute('SELECT * FROM CalibrationPairDistances WHERE calibration_id=?',(calibration_id,)))
    kinds={v:k for k,v in params['feature_versions'].items()}
    if len(distances)!=80000:raise ValueError('Expected 80,000 component pair distances')
    for r in distances:
        if r['feature_version'] not in kinds or r['distance']!=float(csv_pairs[r['pair_index']]['distance_'+kinds[r['feature_version']]]):
            raise ValueError('Calibration pair distance mismatch')
    return params


class SqlFourGallery:
    """Vectors, metadata and calibration loaded from SQLite, no NPY/CSV gallery reads."""
    resolve=fusion.FourGallery.resolve

    def __init__(self,c,calibration_id=CALIBRATION_ID):
        migration=c.execute('SELECT * FROM FourFeatureMigrations WHERE extension_version=?',(EXTENSION,)).fetchone()
        if (migration is None or migration['migration_sha256']!=MIGRATION_SHA
                or migration['authority_sha256']!=AUTHORITY_SHA or db.sha_bytes(migration['authority_data'])!=AUTHORITY_SHA
                or migration['policy_sha256']!=fusion.POLICY_SHA256 or db.sha_bytes(migration['policy_data'])!=fusion.POLICY_SHA256):
            raise ValueError('Database extension/authority/policy mismatch')
        self.auth=json.loads(migration['authority_data']);self.policy=json.loads(migration['policy_data'])
        if migration['source_database_sha256']!=self.auth['source_database_sha256']:raise ValueError('Source DB provenance mismatch')
        # Only algorithm source is needed from files; no vector/calibration file dependency.
        for name in ['retrieval/fusion_four.py','database/store.py']:
            p=ROOT/name
            if db.digest(p)!=self.auth['fingerprint'][str(p)]:raise ValueError('Accepted numerical/serialization module changed')
        self.params=load_calibration(c,self.auth,self.policy,calibration_id)
        self.calibration_id=calibration_id
        self.calibration_hash=self.auth['fingerprint'][str(fusion.OUT/'calibration/median_params.json')]
        self.by_id={r['image_id']:dict(image_id=r['image_id'],filename=r['filename'],image_path=r['image_path'],
            source=r['source'].casefold(),image_sha256=r['image_hash'],vector_rows={}) for r in c.execute('SELECT * FROM Images')}
        if len(self.by_id)!=1438:raise ValueError('Expected 1438 image metadata records')
        self.maps={};self.vectors={};self.valid={};missing=[]
        locks={r['kind']:r for r in c.execute('SELECT * FROM FourFeatureVersionLocks')}
        if set(locks)!=set(fusion.KINDS):raise ValueError('Missing feature version locks')
        for r in c.execute('SELECT * FROM FourFeatureArtifacts'):
            expected=self.policy['input_files'].get(r['source_path'])
            if expected!=r['artifact_sha256'] or db.sha_bytes(r['artifact_data'])!=expected:
                raise ValueError('Stored feature artifact/source hash mismatch')
        for kind in fusion.KINDS:
            version=self.params['feature_versions'][kind];lock=locks[kind]
            version_row=c.execute('SELECT * FROM FeatureVersions WHERE feature_version=?',(version,)).fetchone()
            if lock['feature_version']!=version or version_row is None or record_hash(version_row)!=lock['version_record_sha256']:
                raise ValueError('Wrong feature version/schema lock')
            if version_row['dimension']!=fusion.DIMENSIONS[kind] or version_row['dtype']!='<f8':raise ValueError('Feature dtype/dimension mismatch')
            filename='features_'+kind.upper()+('_normalized.npy' if kind in ('a','b') else '.npy')
            expected=[value for name,value in self.policy['input_files'].items() if Path(name).name==filename]
            if len(expected)!=1 or lock['vector_artifact_sha256']!=expected[0]:raise ValueError('Vector artifact version/hash mismatch')
            self.valid[kind]={};self.maps[kind]={}
            rows=list(c.execute('''SELECT v.*,b.source_row_index,b.source_vector_sha256,b.source_image_sha256
                FROM FeatureVectors v LEFT JOIN FourFeatureVectorBindings b USING(image_id,feature_version)
                WHERE v.feature_version=?''',(version,)))
            if len(rows)!=1438 or {r['image_id'] for r in rows}!=set(self.by_id):raise ValueError('Feature metadata coverage mismatch')
            for r in rows:
                key=r['image_id'];self.by_id[key]['vector_rows'][kind]=r['feature_row_index']
                if r['status']=='missing':
                    if kind!='b' or key!='hf_merged_00209' or r['vector_data'] is not None or r['missing_reason']!='hair:missing_empty(0<100)':
                        raise ValueError('Unexpected missing feature; no imputation')
                    missing.append(dict(image_id=key,reason=r['missing_reason']));continue
                if (r['source_vector_sha256']!=r['vector_sha256'] or r['source_row_index']!=r['feature_row_index']
                        or r['source_image_sha256']!=self.by_id[key]['image_sha256']
                        or r['dimension']!=fusion.DIMENSIONS[kind] or r['dtype']!='<f8'):
                    raise ValueError('Vector source/index/dtype/dimension mismatch')
                value=db.decode_vector(r['vector_data'],r['dtype'],r['dimension'],r['source_vector_sha256'])
                self.valid[kind][key]=value;self.maps[kind][key]=r['feature_row_index']
            if len(self.valid[kind])!=self.policy['expected_counts'][kind]:raise ValueError('Feature valid count mismatch')
            if kind in ('a','b'):db.load_stats(c,version)
        self.ids=sorted(set.intersection(*(set(v) for v in self.valid.values())))
        if self.ids!=self.params['image_ids'] or len(self.ids)!=1437 or len(missing)!=1:raise ValueError('Four-way intersection mismatch')
        self.positions={key:i for i,key in enumerate(self.ids)}
        for kind in fusion.KINDS:
            self.vectors[kind]=np.stack([self.valid[kind][key] for key in self.ids]);self.vectors[kind].flags.writeable=False
        if (np.any(self.vectors['c1']<0) or not np.allclose(self.vectors['c1'].reshape(-1,4,59).sum(axis=2),1,atol=1e-12,rtol=0)
                or np.any(self.vectors['c2']<0) or not np.allclose(np.linalg.norm(self.vectors['c2'],axis=1),1,atol=1e-12,rtol=0)):
            raise ValueError('Existing C1 L1/C2 L2 normalization contract mismatch')
        self.ab=SimpleNamespace(missing_b=missing)


def query(c,image,*,top_k=5,weights=(.25,.25,.25,.25),persist=True,gallery=None,calibration_id=CALIBRATION_ID):
    w=fusion.validate_weights(weights)
    if type(top_k)is not int or top_k<=0:raise ValueError('top_k must be positive integer')
    g=gallery or SqlFourGallery(c,calibration_id)
    if g.calibration_id!=calibration_id:raise ValueError('Cached gallery calibration mismatch')
    key=g.resolve(image);excluded=int(key in g.positions)
    result=dict(schema_id='FOUR_FEATURE_SQLITE_QUERY_v1',query=g.by_id[key],feature_versions=g.params['feature_versions'],
        calibration_id=calibration_id,calibration_params_sha256=g.calibration_hash,policy_sha256=fusion.POLICY_SHA256,
        medians=g.params['medians'],epsilon=fusion.EPSILON,epsilon_c1=fusion.EPSILON_C1,
        weights={k:float(w[i]) for i,k in enumerate(fusion.KINDS)},
        weight_configuration='EXPERIMENTAL_EQUAL_WEIGHTS' if np.array_equal(w,[.25]*4) else 'USER_SUPPLIED_WEIGHTS',
        gallery_intersection_count=len(g.ids),self_exclusion_count=excluded,candidate_count=len(g.ids)-excluded,
        ranked_candidate_count=0,top_k=top_k,status='ok',missing_reason=None,modes={m:[] for m in MODES},
        new_image_support=False,tie_break='distance then image_id',vector_storage='SQLite typed BLOB; independent vectors')
    if not excluded:
        result.update(status='fusion_unavailable',missing_feature='missing_B',available_features=['a','c1','c2'],
            missing_reason=next(r['reason'] for r in g.ab.missing_b if r['image_id']==key))
    else:
        raw=fusion.component_distances({k:g.vectors[k][g.positions[key]] for k in fusion.KINDS},g.vectors)
        normalized,total=fusion.combine(raw,g.params,w)
        result['ranked_candidate_count']=result['candidate_count']
        for mode in MODES:
            scores=total if mode=='fusion' else raw[mode]
            for rank,i in enumerate(fusion.rank_indices(g.ids,scores,key,top_k),1):
                r=g.by_id[g.ids[i]]
                result['modes'][mode].append(dict(mode=mode,rank=rank,image_id=r['image_id'],filename=r['filename'],source=r['source'],
                    score=float(scores[i]),**{'distance_'+k:float(raw[k][i]) for k in fusion.KINDS},
                    **{'normalized_'+k:float(normalized[k][i]) for k in fusion.KINDS},D=float(total[i]),
                    **{k+'_row_index':r['vector_rows'][k] for k in fusion.KINDS}))
    if persist:
        run_id=str(uuid.uuid4())
        with c:
            db.insert_row(c,'FourFeatureRuns',dict(run_id=run_id,created_at=db.utc_now(),query_image_id=key,
                query_path=g.by_id[key]['image_path'],query_sha256=g.by_id[key]['image_sha256'],calibration_id=calibration_id,
                **{'weight_'+k:float(w[i]) for i,k in enumerate(fusion.KINDS)},top_k=top_k,status=result['status'],
                missing_reason=result['missing_reason'],**{k:result[k] for k in
                    ['gallery_intersection_count','candidate_count','self_exclusion_count','ranked_candidate_count']},
                provenance_json=db.json_text(dict(policy_sha256=fusion.POLICY_SHA256,calibration_params_sha256=g.calibration_hash,
                    extension=EXTENSION,query_input=str(image),weight_configuration=result['weight_configuration'],
                    metrics='Euclid A/B/C2; Chi-square C1 coefficient0.5; existing fusion_four functions'))))
            for i,k in enumerate(fusion.KINDS):
                db.insert_row(c,'FourFeatureRunComponents',dict(run_id=run_id,calibration_id=calibration_id,kind=k,
                    feature_version=g.params['feature_versions'][k],weight=float(w[i]),median=g.params['medians'][k]))
            for mode,rows in result['modes'].items():
                for r in rows:
                    db.insert_row(c,'FourFeatureResults',dict(run_id=run_id,mode=mode,rank=r['rank'],image_id=r['image_id'],
                        dA=r['distance_a'],dB=r['distance_b'],dC1=r['distance_c1'],dC2=r['distance_c2'],
                        **{'normalized_'+k:r['normalized_'+k] for k in fusion.KINDS},D=r['D'],score=r['score']))
        result['run_id']=run_id
    else:result['run_id']=None
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['import','search','info','backup']:
        p=sub.add_parser(name);p.add_argument('--db',type=Path,default=DEFAULT_DB)
        if name=='search':
            p.add_argument('--image',required=True);p.add_argument('--top-k',type=int,default=5)
            for k in fusion.KINDS:p.add_argument('--weight-'+k,type=float,default=.25)
            p.add_argument('--no-save',action='store_true');p.add_argument('--output',type=Path)
        if name=='backup':p.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='import':result=import_database(args.db)
    elif args.command=='backup':result=db.backup(args.db,args.destination)
    else:
        if args.command=='search' and args.output and args.output.exists():raise FileExistsError('Query JSON exists')
        with closing(db.connect(args.db,readonly=args.command!='search' or args.no_save)) as c:
            if args.command=='info':result=summary(c)
            else:result=query(c,args.image,top_k=args.top_k,weights=[getattr(args,'weight_'+k) for k in fusion.KINDS],persist=not args.no_save)
        if args.command=='search' and args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
