"""Staged C2 extraction: synthetic gate -> trial100 oracle -> full1438."""
import argparse
import shutil
import sys
from collections import Counter

import cv2
import numpy as np

from . import root_hog as hog
from .common import BASE,ROOT,TRIAL_PLAN,read_json,write_json,save_csv,catalog,identities,baseline_check


def run(stage):
    out=BASE/('trial100' if stage=='trial' else 'full_v1')
    if out.exists():raise FileExistsError('C2 stage output exists; no overwrite')
    baseline=baseline_check();lock=hog.lock();preflight=read_json(BASE/'evidence/preflight_tests.json')
    if not preflight['successful']:raise ValueError('Synthetic C2 tests have not passed')
    if stage=='full':
        trial=read_json(BASE/'trial100/verification.json')
        if trial['numerical_status']!='PASS' or any(trial.get(k)!=v for k,v in lock.items()):
            raise ValueError('Trial100 oracle gate missing, failed or stale')
    images=catalog()
    if stage=='trial':
        plan=read_json(TRIAL_PLAN);ids=[r['image_id'] for r in plan['images']]
        if len(ids)!=100 or len(set(ids))!=100:raise ValueError('Invalid frozen C1 trial100 plan')
    else:ids=identities(list(images.values()))
    out.mkdir()
    if stage=='trial':shutil.copyfile(TRIAL_PLAN,out/'input_manifest_C1_trial100.json')
    schema=dict(schema_id='C2_ROOT_HOG324_FEATURE_SCHEMA_v1',**lock,logical_group='C',feature_name='C2',
        dimension=324,dtype='float64',cell_shape=[4,4,9],block_shape=[9,36],ROI_width_height=[160,192],
        crop_xyxy_exclusive=[48,32,208,224],normalization='Root per block with epsilon1e-8; exact global L2',
        distance='Euclid324',anatomical_crop_status='UNVERIFIED_CENTER_CROP_PROTOTYPE',
        spec=hog.load_spec(),environment=dict(python=sys.version,numpy=np.__version__,opencv=cv2.__version__),
        source_C1_manifest_sha256=hog.sha256(TRIAL_PLAN),catalog_sha256=hog.sha256(ROOT/'database/data/portrait_ab_v2.sqlite3'))
    schema['content_sha256']=hog.content_hash(schema);write_json(out/'feature_schema.json',schema)
    features=[];cells=[];blocks=[];roots=[];feature_rows=[];status_rows=[]
    for n,identity in enumerate(ids,1):
        image=images[identity]
        if hog.sha256(image['image_path'])!=image['image_hash']:raise ValueError('Source image hash mismatch')
        result=hog.extract_c2(cv2.imread(image['image_path'],cv2.IMREAD_UNCHANGED));index=''
        if result['status']=='valid_C2':
            index=len(features);features.append(result['vector']);cells.append(result['cells'])
            blocks.append(result['blocks']);roots.append(result['root_blocks'])
            feature_rows.append(dict(feature_row_index=index,image_id=identity,filename=image['filename'],image_path=image['image_path'],
                source=image['source'],image_sha256=image['image_hash'],crop_x0=48,crop_y0=32,crop_x1_exclusive=208,crop_y1_exclusive=224,
                **lock))
        status_rows.append(dict(image_id=identity,filename=image['filename'],source=image['source'],status=result['status'],
            missing_reason=result['missing_reason'] or '',feature_row_index=index,image_sha256=image['image_hash'],
            crop_x0=48,crop_y0=32,crop_x1_exclusive=208,crop_y1_exclusive=224,**lock))
        if n%100==0 or n==len(ids):print(stage,n,'/',len(ids),'processed;',len(features),'valid C2',flush=True)
    arrays={'features_C2.npy':np.stack(features) if features else np.empty((0,324),np.float64),
        'raw_cells.npy':np.stack(cells) if cells else np.empty((0,4,4,9),np.float64),
        'raw_blocks.npy':np.stack(blocks) if blocks else np.empty((0,9,36),np.float64),
        'root_blocks.npy':np.stack(roots) if roots else np.empty((0,9,36),np.float64)}
    for name,array in arrays.items():
        with (out/name).open('xb') as stream:np.save(stream,array,allow_pickle=False)
    fields=['feature_row_index','image_id','filename','image_path','source','image_sha256','crop_x0','crop_y0','crop_x1_exclusive','crop_y1_exclusive',*lock]
    save_csv(out/'feature_rows.csv',feature_rows,fields);save_csv(out/'extraction_status.csv',status_rows)
    write_json(out/'manifest.json',dict(schema_id='C2_BATCH_MANIFEST_v1',**lock,stage=stage,processed=len(ids),valid=len(features),
        missing=len(ids)-len(features),input_ids=ids,source_counts=dict(Counter(r['source'] for r in status_rows)),
        valid_source_counts=dict(Counter(r['source'] for r in feature_rows)),
        schema_content_sha256=schema['content_sha256'],source_trial_manifest_sha256=hog.sha256(TRIAL_PLAN),
        artifacts={name:dict(sha256=hog.sha256(out/name),bytes=(out/name).stat().st_size)
            for name in [*arrays,'feature_rows.csv','extraction_status.csv','feature_schema.json']},
        immutable_baseline_files=len(baseline),new_detector_alignment_runs=0,SQLite_writes=0,C1_features_used=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=['trial','full'],required=True)
    run(parser.parse_args().stage)


if __name__=='__main__':main()
