"""Independent tabular checks, intersection diagnostics and frozen-input audit."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib
import json

import cv2
import numpy as np

import validate_roi_all as audit
from shared.report_v2 import read_json,read_csv,write_json


def segment_intersections(vertices):
    """Scalar determinant calculation, independent of the original boolean check."""
    result=[]
    def cross(a,b):return float(a[0])*float(b[1])-float(a[1])*float(b[0])
    n=len(vertices)
    for i in range(n):
        a=vertices[i];r=vertices[(i+1)%n]-a
        for j in range(i+2,n):
            if i==0 and j==n-1:continue
            c=vertices[j];s=vertices[(j+1)%n]-c
            denominator=cross(r,s)
            if abs(denominator)<1e-12:continue
            t=cross(c-a,s)/denominator;u=cross(c-a,r)/denominator
            if 0<t<1 and 0<u<1:
                result.append(dict(edge_a=[i,(i+1)%n],edge_b=[j,(j+1)%n],
                    intersection_xy=(a+t*r).tolist(),segment_parameters=[t,u]))
    return result


def main():
    out=audit.OUT
    summary=read_json(out/'summary.json')
    rows=read_csv(out/'metrics.csv');imrows=read_csv(out/'image_metrics.csv')
    pairs=read_csv(out/'overlap_metrics.csv');vertices=read_csv(out/'roi_vertices.csv')
    assert len(rows)==5752 and len(imrows)==1438 and len(pairs)==8628 and len(vertices)==87718
    assert len({(r['image_id'],r['region']) for r in rows})==5752
    assert Counter(r['region'] for r in rows)=={key:1438 for key in audit.REGIONS}
    assert len({r['image_id'] for r in imrows})==1438
    by_image=defaultdict(dict)
    for r in rows:by_image[r['image_id']][r['region']]=r
    for r in imrows:
        local=by_image[r['image_id']]
        raw_sum=sum(int(x['raw_mask_pixels']) for x in local.values())
        # Here max membership=2; verify inclusion-exclusion independently.
        overlaps=sum(int(p['overlap_pixels']) for p in pairs if p['image_id']==r['image_id'])
        assert int(r['max_memberships'])==2
        assert raw_sum-overlaps==int(r['raw_union_pixels'])
    contract=read_json(out/'contract_v0_2.json')
    content=contract.pop('content_sha256')
    assert audit.canonical_hash(contract)==content
    assert audit.digest(out/'contract_v0_2.json')==summary['contract_file_sha256']
    assert contract['polygons']==read_json(audit.PROPOSAL)['polygons']
    assert contract['priority_subtraction_applied'] is False
    vertex_groups=defaultdict(list)
    for r in vertices:vertex_groups[(r['image_id'],r['region'])].append(r)
    anomalies=[]
    for row in rows:
        if row['geometry_valid']=='True':continue
        v=sorted(vertex_groups[(row['image_id'],row['region'])],key=lambda r:int(r['vertex_order']))
        xy=np.array([[float(r['x']),float(r['y'])] for r in v])
        intersections=segment_intersections(xy)
        assert intersections, 'Expected proper self-intersection, not merely a generic invalid flag'
        for crossing in intersections:
            crossing['endpoint_refs']={key:[{field:v[i][field] for field in ['ref','source_index','mediapipe_index','offset_u_ipd','offset_v_ipd']}
                for i in crossing[key]] for key in ['edge_a','edge_b']}
        anomalies.append(dict(image_id=row['image_id'],region=row['region'],confirmed_reason='proper_self_intersection',
            intersections=intersections,zero_length_edges=bool(np.any(np.linalg.norm(xy-np.roll(xy,-1,axis=0),axis=1)<1e-9))))
    assert len(anomalies)==summary['geometry_invalid_rois']==4
    write_json(out/'geometry_anomalies.json',anomalies)
    codebook=read_csv(out/'nri_uniform_59_codebook.csv')
    labels={int(r['raw_code']):int(r['nri_uniform_bin']) for r in codebook}
    uniform=set([0,255])
    for ones in range(1,8):
        base=(1<<ones)-1
        for rotation in range(8):
            word=((base>>rotation)|(base<<(8-rotation)))&255
            assert labels[word]==1+8*(ones-1)+rotation
            uniform.add(word)
    assert len(uniform)==58 and labels[0]==0 and labels[255]==57
    assert all(labels[c]==58 for c in range(256) if c not in uniform)
    assert len({labels[c] for c in uniform})==58
    case_data=read_json(out/'case_selection.json')
    for case in case_data['cases']:
        key=case['image_id'];masks=[]
        for region in audit.REGIONS:
            p=out/'contact_sheets'/key/(region+'_raw_mask.png')
            mask=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
            assert mask is not None and set(np.unique(mask)).issubset({0,255})
            b=(mask!=0).astype(np.uint8)
            assert hashlib.sha256(b.tobytes()).hexdigest()==by_image[key][region]['raw_mask_sha256']
            masks.append(b)
        assert (np.sum(masks,axis=0)>=2).any(), 'Selected raw masks must retain measured overlap'
    trial=read_json(out/'trial100_manifest.json')
    assert len(trial['images'])==100 and len({r['image_id'] for r in trial['images']})==100
    assert Counter(r['source'].lower() for r in trial['images'])==dict(cfd=50,hf=50)
    assert {r['image_id'] for r in trial['images'] if not r['technical_roi_support_ready']}=={r['image_id'] for r in anomalies}
    assert not list(out.rglob('*.npy')) and not list(out.rglob('*.npz'))
    baseline=read_json(out/'baseline_before.json')
    changed=[p for p,h in baseline.items() if audit.digest(p)!=h]
    assert not changed,changed
    report=dict(status='PASS',roi_metric_rows=5752,image_metric_rows=1438,vertex_rows=len(vertices),
        pair_metric_rows=8628,anomalous_rois=4,independent_intersection_confirmation=True,
        codebook_uniform_patterns=58,codebook_nonuniform_patterns=198,codebook_bins=59,
        raw_mask_png_roundtrips=len(case_data['cases'])*4,overlap_retained=True,priority_subtraction_applied=False,
        trial_manifest_count=100,trial_processable=96,trial_expected_reject=4,trial_executed=False,
        protected_files_checked=len(baseline),changed_existing_files=changed,
        c1_c2_vectors_created=False,lbp_extractor_written=False,approval_status='PROVISIONAL')
    write_json(out/'verification.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
