"""Staged independent scalar verification before full extraction and final C2 regression."""
from pathlib import Path
import argparse
import io
import json
import math
import sys
import unittest

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from features.C2_hog.src import root_hog as hog
from features.C2_hog.src.common import BASE,read_json,read_csv,write_json,baseline_check,identities
from features.C2_hog.verification import scalar_oracle as oracle
from retrieval.search_c2 import C2Gallery

FULL_SAMPLES=['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00069','hf_merged_00198','hf_merged_00209',
              'hf_merged_00267','hf_merged_00333','hf_merged_00463','hf_merged_00561','hf_merged_00694','hf_merged_00722']


def run(stage):
    directory=BASE/('trial100' if stage=='trial' else 'full_v1')
    if (directory/'verification.json').exists():raise FileExistsError('Stage verification exists')
    gallery=C2Gallery(directory);spec=hog.load_spec();tol=spec['implementation_details']['oracle_tolerances']
    matrix=gallery.matrix;cells=np.load(directory/'raw_cells.npy',allow_pickle=False)
    blocks=np.load(directory/'raw_blocks.npy',allow_pickle=False);roots=np.load(directory/'root_blocks.npy',allow_pickle=False)
    assert cells.shape==(len(matrix),4,4,9) and blocks.shape==roots.shape==(len(matrix),9,36)
    for array in [matrix,cells,blocks,roots]:assert array.dtype==np.float64 and np.isfinite(array).all() and np.all(array>=0)
    reconstructed_blocks=np.stack([np.stack([c[y:y+2,x:x+2].reshape(36) for y in range(3) for x in range(3)]) for c in cells])
    np.testing.assert_array_equal(blocks,reconstructed_blocks)
    np.testing.assert_array_equal(roots,np.sqrt(blocks/(blocks.sum(axis=2,keepdims=True)+1e-8)))
    flattened=roots.reshape(-1,324);np.testing.assert_array_equal(matrix,flattened/np.sqrt(np.sum(flattened*flattened,axis=1))[:,None])
    samples=list(gallery.manifest['input_ids']) if stage=='trial' else FULL_SAMPLES
    max_errors={key:0. for key in ['gray','gx','gy','magnitude','orientation','cells','blocks','root_blocks','vector']}
    oracle_records=[];hand=None
    for n,identity in enumerate(samples,1):
        row=gallery.status[identity];image=None
        if identity not in gallery.by_id:
            assert row['status']=='missing_C2' and row['missing_reason'] and row['feature_row_index']==''
            # Source path is available from the immutable catalog for a rejected image.
            from features.C2_hog.src.common import catalog
            image=cv2.imread(catalog()[identity]['image_path'],cv2.IMREAD_UNCHANGED)
        else:image=cv2.imread(gallery.by_id[identity]['image_path'],cv2.IMREAD_UNCHANGED)
        expected=oracle.extract(image);actual=hog.extract_c2(image)
        if expected['vector'] is None:
            assert actual['vector'] is None and identity not in gallery.by_id;continue
        assert actual['status']=='valid_C2' and identity in gallery.by_id
        for key in max_errors:
            if key in ['gray','gx','gy']:np.testing.assert_array_equal(actual[key],expected[key])
            elif key in ['magnitude','orientation']:np.testing.assert_allclose(actual[key],expected[key],rtol=0,atol=1e-12)
            elif key in ['cells','blocks']:np.testing.assert_allclose(actual[key],expected[key],rtol=tol['cell_hist_rel'],atol=tol['cell_hist_abs'])
            else:np.testing.assert_allclose(actual[key],expected[key],rtol=0,atol=tol['root_or_final_abs'])
            max_errors[key]=max(max_errors[key],float(np.max(np.abs(actual[key]-expected[key]))))
        i=int(gallery.by_id[identity]['feature_row_index'])
        for stored,key in [(matrix,'vector'),(cells,'cells'),(blocks,'blocks'),(roots,'root_blocks')]:
            np.testing.assert_array_equal(stored[i],actual[key])
        oracle_records.append(dict(image_id=identity,gradient_centres=30020,raw_cells=16,root_blocks=9,independent_scalar_match=True))
        if identity=='cfd_final_00001':
            y,x=96,80;theta=float(expected['orientation'][y,x]);bin_number=int(theta//20);cy,cx=y//48,x//40
            block_y,block_x=1,1;block_index=4;component=((cy-block_y)*2+(cx-block_x))*9+bin_number
            hand=dict(image_id=identity,ROI_pixel_xy=[x,y],source_pixel_xy=[x+48,y+32],
                gray_left_right_up_down=[float(expected['gray'][y,x-1]),float(expected['gray'][y,x+1]),float(expected['gray'][y-1,x]),float(expected['gray'][y+1,x])],
                Gx=float(expected['gx'][y,x]),Gy=float(expected['gy'][y,x]),magnitude=float(expected['magnitude'][y,x]),
                unsigned_orientation=theta,bin=bin_number,cell_yx=[cy,cx],single_pixel_vote=float(expected['magnitude'][y,x]),
                total_cell_bin=float(expected['cells'][cy,cx,bin_number]),block_index=block_index,block_origin_cell_yx=[1,1],
                block_component=component,block_sum=math.fsum(expected['blocks'][block_index]),
                expected_root_component=float(expected['root_blocks'][block_index,component]),
                normalized_final_component=float(expected['vector'][block_index*36+component]))
        if n%10==0 or n==len(samples):print(stage,'scalar oracle',n,'/',len(samples),'images',flush=True)
    assert identities(gallery.rows)==identities(list(reversed(gallery.rows)))
    if stage=='full':
        old=C2Gallery(BASE/'trial100')
        for row in old.rows:np.testing.assert_array_equal(gallery.vector(row['image_id']),old.vector(row['image_id']))
    # Query-stage numerical checks use the same fixed cases, never to choose crop/conventions.
    distance_error=0.;ranking_records=[]
    for identity in FULL_SAMPLES:
        if identity not in gallery.by_id:continue
        q=gallery.vector(identity);expected=[oracle.euclid(q,v) for v in matrix]
        actual=np.sqrt(np.sum((matrix-q)**2,axis=1));error=float(np.max(np.abs(actual-expected)))
        distance_error=max(distance_error,error);assert error<=tol['Euclid_abs']
        index=int(gallery.by_id[identity]['feature_row_index']);assert expected[index]==actual[index]==0.
        ordered=sorted((i for i,row in enumerate(gallery.rows) if row['image_id']!=identity),key=lambda i:(expected[i],gallery.rows[i]['image_id']))[:5]
        _,ranked=gallery.search(identity)
        assert [r['image_id'] for r in ranked]==[gallery.rows[i]['image_id'] for i in ordered]
        ranking_records.append(dict(query=identity,top5=[r['image_id'] for r in ranked],scalar_distance_max_abs_error=error))
    modules=['test_c2_root_hog.py']
    if stage=='full':modules+=['test_c2_pipeline.py','test_report_v2.py','test_search_ab.py','test_color_features.py',
        'test_color_report_compliance.py','test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py']
    suite=unittest.TestSuite()
    for filename in modules:suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=filename))
    output=io.StringIO();tests=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    with (directory/'tests.log').open('x',encoding='utf-8') as stream:stream.write(output.getvalue())
    print(output.getvalue(),end='',flush=True)
    assert tests.wasSuccessful() and not tests.skipped
    baseline=baseline_check()
    write_json(directory/'hand_calculation.json',hand)
    write_json(directory/'verification.json',dict(schema_id='C2_NUMERICAL_VERIFICATION_v1',**hog.lock(),stage=stage,numerical_status='PASS',
        processed=gallery.manifest['processed'],valid=len(matrix),missing=gallery.manifest['missing'],
        scalar_images=len(samples),scalar_gradient_centres=30020*len(oracle_records),max_abs_errors=max_errors,
        scalar_image_records=oracle_records,scalar_distance_max_abs_error=distance_error,scalar_rankings=ranking_records,
        tests_run=tests.testsRun,test_failures=len(tests.failures),test_errors=len(tests.errors),skipped=len(tests.skipped),
        vector_shape=list(matrix.shape),dtype=str(matrix.dtype),L2_min=float(np.linalg.norm(matrix,axis=1).min()),
        L2_max=float(np.linalg.norm(matrix,axis=1).max()),raw_cells_shape=list(cells.shape),root_blocks_shape=list(roots.shape),
        metadata_permutation_invariant=True,protected_files=len(baseline),old_files_changed=[],
        crop_anatomy='UNVERIFIED_CENTER_CROP_PROTOTYPE',fusion=False,C1_full_batch_rerun=False))
    print(stage,'PASS; independent scalar images',len(samples),'tests',tests.testsRun,'old artifacts unchanged',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['trial','full'],required=True);run(parser.parse_args().stage)


if __name__=='__main__':main()
