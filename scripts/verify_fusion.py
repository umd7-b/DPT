"""Scalar oracle for all 20k pairs, complete rankings, and CSV/JSON/PNG evidence."""
from pathlib import Path
import hashlib
import json
import math
import sys
import unittest

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from retrieval import fusion_four as f
from retrieval import fusion_oracle as oracle
from retrieval import search_fusion as production
from shared.report_v2 import read_json,read_csv,write_json,save_csv

EVIDENCE=f.OUT/'evidence'
QUERY_IDS=['cfd_final_00001','cfd_final_00069','hf_merged_00001','hf_merged_00198','hf_merged_00722']


def require_close(actual,expected):
    np.testing.assert_allclose(actual,expected,atol=1e-12,rtol=1e-12)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if (EVIDENCE/'verification.json').exists():raise FileExistsError('Verification exists; do not overwrite evidence')
    g=f.FourGallery();params=f.load_calibration(g)
    vectors=oracle.load_vectors(ROOT)
    ids=sorted(set.intersection(*(set(vectors[k]) for k in oracle.KINDS)))
    assert ids==g.ids and len(ids)==1437
    for kind in oracle.KINDS:
        assert len(vectors[kind])==g.policy['expected_counts'][kind]
    frozen=oracle.rows(f.AB_CALIBRATION/'representative_pairs.csv')
    pairs=[(r['image_id_1'],r['image_id_2']) for r in frozen]
    ids_hash=hashlib.sha256(json.dumps(pairs,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()
    assert ids_hash==g.policy['pair_ids_sha256'] and len(pairs)==20000
    assert all(a in ids and b in ids and a<b for a,b in pairs)
    csv_rows=oracle.rows(f.OUT/'calibration/representative_pairs.csv')
    scalar_pairs=[];max_errors={k:0. for k in oracle.KINDS}
    for n,(left,right) in enumerate(pairs):
        expected=oracle.distances(vectors,left,right)
        actual=csv_rows[n]
        assert actual['image_id_1']==left and actual['image_id_2']==right and int(actual['pair_id'])==n
        scalar_pairs.append(dict(pair_id=n,image_id_1=left,image_id_2=right,
                                 **{'distance_'+k:expected[k] for k in oracle.KINDS}))
        for kind in oracle.KINDS:
            value=float(actual['distance_'+kind]);require_close(value,expected[kind])
            max_errors[kind]=max(max_errors[kind],abs(value-expected[kind]))
        for kind in ['a','b']:require_close(float(actual['distance_'+kind]),float(frozen[n]['distance_'+kind]))
    scalar_medians={k:oracle.median([r['distance_'+k] for r in scalar_pairs]) for k in oracle.KINDS}
    for kind in oracle.KINDS:require_close(params['medians'][kind],scalar_medians[kind])
    for kind in ['a','b']:require_close(params['medians'][kind],g.ab_params['median_'+kind])
    print('Independent 20,000 pairs and four medians: PASS',flush=True)
    save_csv(EVIDENCE/'scalar_calibration_pairs.csv',scalar_pairs)
    query_distances=[];rankings=[];tile_count=0;text_strips=0;max_query_errors={k:0. for k in oracle.KINDS};max_D_error=0.
    for query in QUERY_IDS:
        expected,scores,orders=oracle.ranking(vectors,ids,query,scalar_medians)
        actual=production.search(g,params,query,2000)
        assert actual['candidate_count']==1436 and actual['self_exclusion_count']==1
        assert actual['ranked_candidate_count']==1436
        by_id={r['image_id']:r for r in actual['modes']['fusion']}
        for kind in production.MODES:
            assert [r['image_id'] for r in actual['modes'][kind]]==orders[kind]
            assert set(orders[kind])==set(ids)-{query}
        for key,raw in expected.items():
            actual_row=by_id[key]
            normalized={k:raw[k]/(scalar_medians[k]+1e-8) for k in oracle.KINDS}
            for kind in oracle.KINDS:
                require_close(actual_row['distance_'+kind],raw[kind]);require_close(actual_row['normalized_'+kind],normalized[kind])
                max_query_errors[kind]=max(max_query_errors[kind],abs(actual_row['distance_'+kind]-raw[kind]))
            require_close(actual_row['D'],scores[key]);max_D_error=max(max_D_error,abs(actual_row['D']-scores[key]))
            ab_score=math.fsum([.5*raw['a']/(g.ab_params['median_a']+1e-8),.5*raw['b']/(g.ab_params['median_b']+1e-8)])
            query_distances.append(dict(query=query,candidate=key,**{'distance_'+k:raw[k] for k in oracle.KINDS},
                **{'normalized_'+k:normalized[k] for k in oracle.KINDS},D=scores[key],D_AB=ab_score))
        ab_scores={r['candidate']:r['D_AB'] for r in query_distances if r['query']==query}
        ab_order=sorted(ab_scores,key=lambda key:(ab_scores[key],key))
        rankings.append(dict(query=query,candidates=1436,all_modes_full_ranking_equal=True,
            top5={k:orders[k][:5] for k in production.MODES},ab_top5=ab_order[:5],
            top5_AB_fusion_overlap=len(set(ab_order[:5])&set(orders['fusion'][:5])),
            ranking_positions_changed_AB_vs_fusion=sum(a!=b for a,b in zip(ab_order,orders['fusion'],strict=True))))
        # Compare saved CLI artifacts, not freshly serialized production output.
        folder=f.OUT/'queries'/query
        saved=read_json(folder/'results.json');table=oracle.rows(folder/'results.csv')
        assert saved['medians']==params['medians'] and saved['weights']==dict.fromkeys(oracle.KINDS,.25)
        assert saved['candidate_count']==1436 and saved['self_exclusion_count']==1 and saved['ranked_candidate_count']==1436
        assert len(table)==25
        image=cv2.imread(str(folder/'comparison.png'),cv2.IMREAD_UNCHANGED)
        assert image.shape==(1640,1536,3)
        for row_index,kind in enumerate(production.MODES):
            stored=saved['modes'][kind]
            assert [r['image_id'] for r in stored]==orders[kind][:5]
            for i,r in enumerate(stored):
                csv_row=table[row_index*5+i]
                assert set(csv_row)==set(production.FIELDS)
                for field in production.FIELDS:
                    if field in ('mode','image_id','filename','source'):assert csv_row[field]==r[field]
                    else:assert float(csv_row[field])==float(r[field])
                assert r['filename']==g.by_id[r['image_id']]['filename']
                for k in oracle.KINDS:
                    require_close(r['distance_'+k],expected[r['image_id']][k])
                    require_close(r['normalized_'+k],expected[r['image_id']][k]/(scalar_medians[k]+1e-8))
                require_close(r['D'],scores[r['image_id']])
                require_close(r['score'],scores[r['image_id']] if kind=='fusion' else expected[r['image_id']][kind])
            entries=[dict(g.by_id[query],rank=0)]+stored
            for col,entry in enumerate(entries):
                source=g.by_id[entry['image_id']];x,y=col*256,40+row_index*320
                np.testing.assert_array_equal(image[y:y+256,x:x+256],cv2.imread(source['image_path']))
                assert sha(source['image_path'])==source['image_sha256'];tile_count+=1
                strip=np.full((64,256,3),250,np.uint8)
                title=kind.upper()+(' QUERY' if col==0 else ' #'+str(entry['rank']))
                cv2.putText(strip,title,(5,17),0,.43,(20,20,20),1,cv2.LINE_AA)
                cv2.putText(strip,source['filename'],(5,35),0,.4,(20,20,20),1,cv2.LINE_AA)
                if col:cv2.putText(strip,f"d={entry['score']:.10f}",(5,54),0,.43,(20,20,20),1,cv2.LINE_AA)
                np.testing.assert_array_equal(image[y+256:y+320,x:x+256],strip);text_strips+=1
        for k in oracle.KINDS:assert oracle.distances(vectors,query,query)[k]==0.
        print('Independent full rankings + CSV/JSON/PNG:',query,'PASS',flush=True)
    # A non-equal fixed fixture verifies weights on real data without optimizing them.
    query=QUERY_IDS[0];weights=(.1,.2,.3,.4)
    expected,scores,orders=oracle.ranking(vectors,ids,query,scalar_medians,weights)
    actual=production.search(g,params,query,2000,weights)
    assert [r['image_id'] for r in actual['modes']['fusion']]==orders['fusion']
    for r in actual['modes']['fusion']:require_close(r['D'],scores[r['image_id']])
    missing=read_json(f.OUT/'queries/hf_merged_00209/results.json')
    assert missing['status']=='fusion_unavailable' and missing['missing_feature']=='missing_B'
    assert missing['candidate_count']==1437 and missing['self_exclusion_count']==0 and missing['ranked_candidate_count']==0
    assert not oracle.rows(f.OUT/'queries/hf_merged_00209/results.csv')
    for kind in ['a','c1','c2']:assert 'hf_merged_00209' in vectors[kind]
    assert 'hf_merged_00209' not in vectors['b']
    missing_png=cv2.imread(str(f.OUT/'queries/hf_merged_00209/comparison.png'))
    for i in range(5):
        np.testing.assert_array_equal(missing_png[40+i*320:296+i*320,:256],cv2.imread(g.by_id['hf_merged_00209']['image_path']))
        tile_count+=1
    save_csv(EVIDENCE/'scalar_query_distances.csv',query_distances)
    # Regressions only use fixtures/temp; no batch/extractor or accepted output write.
    suite=unittest.TestSuite()
    for pattern in ['test_report_v2.py','test_search_ab.py','test_color_features.py','test_color_report_compliance.py',
                    'test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py',
                    'test_c2_root_hog.py','test_c2_pipeline.py','test_fusion_four.py']:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    with (EVIDENCE/'tests.log').open('x',encoding='utf8') as stream:
        tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    assert tests.wasSuccessful() and not tests.skipped
    summary=dict(schema_id='FOUR_FEATURE_NUMERICAL_VERIFICATION_v1',status='PASS',
        policy_sha256=f.POLICY_SHA256,independent_oracle='retrieval/fusion_oracle.py: math.fsum scalar; direct source CSV/NPY loading',
        oracle_atol=1e-12,oracle_rtol=1e-12,pairs_verified=20000,pair_ids_sha256=ids_hash,
        pair_distance_max_abs_errors=max_errors,scalar_medians=scalar_medians,stored_medians=params['medians'],
        median_max_abs_error=max(abs(params['medians'][k]-scalar_medians[k]) for k in oracle.KINDS),
        ab_median_abs_deltas={k:abs(params['medians'][k]-g.ab_params['median_'+k]) for k in ['a','b']},
        query_distance_max_abs_errors=max_query_errors,fusion_max_abs_error=max_D_error,
        scalar_rankings=rankings,unequal_weight_fixture=dict(weights=list(weights),query=query,full_ranking_equal=True),
        positive_query_count=5,negative_query_count=1,output_result_rows_verified=125,source_pixel_tiles_verified=tile_count,
        label_distance_text_strips_verified=text_strips,missing_B_status='fusion_unavailable; no result rows',
        tests_run=tests.testsRun,tests_failures=len(tests.failures),tests_errors=len(tests.errors),tests_skipped=len(tests.skipped))
    write_json(EVIDENCE/'verification.json',summary)
    print('Verification PASS; tests:',tests.testsRun,'; tiles:',tile_count,'; four medians:',scalar_medians)


if __name__=='__main__':main()
