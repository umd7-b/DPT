"""Gallery-only four-feature fusion and five comparisons; no extractor or refit."""
from pathlib import Path
import argparse
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from retrieval.fusion_four import (FourGallery,OUT,KINDS,SCHEMA_ID,EPSILON,EPSILON_C1,
    POLICY_SHA256,validate_weights,load_calibration,component_distances,combine,rank_indices)
from shared.report_v2 import digest,save_csv,write_json

MODES=('a','b','c1','c2','fusion')
FIELDS=['mode','rank','image_id','filename','source','score','distance_a','distance_b','distance_c1','distance_c2',
        'normalized_a','normalized_b','normalized_c1','normalized_c2','D','a_row_index','b_row_index','c1_row_index','c2_row_index']


def search(gallery,params,image,top_k=5,weights=(.25,.25,.25,.25)):
    weights=validate_weights(weights)
    if type(top_k) is not int or top_k<=0: raise ValueError('top_k must be positive integer')
    identity=gallery.resolve(image)
    excluded=int(identity in gallery.positions)
    result=dict(schema_id='FOUR_FEATURE_QUERY_v1',calibration_schema=SCHEMA_ID,policy_sha256=POLICY_SHA256,
        feature_versions=gallery.policy['feature_versions'],query=gallery.by_id[identity],
        weights={k:float(weights[i]) for i,k in enumerate(KINDS)},
        weight_configuration='EXPERIMENTAL_EQUAL_WEIGHTS' if np.array_equal(weights,[.25]*4) else 'USER_SUPPLIED_WEIGHTS',
        medians=params['medians'],epsilon=EPSILON,epsilon_c1=EPSILON_C1,pair_ids_sha256=params['pair_ids_sha256'],
        calibration_params_sha256=digest(OUT/'calibration/median_params.json'),
        gallery_intersection_count=len(gallery.ids),self_exclusion_count=excluded,
        candidate_count=len(gallery.ids)-excluded,ranked_candidate_count=0,
        candidate_pool_policy='Same four-complete ID intersection for every mode; remove query image_id',
        top_k=top_k,new_image_support=False,tie_break='distance then image_id',
        modes={m:[] for m in MODES},status='ok',missing_reason=None)
    if identity not in gallery.positions:
        result.update(status='fusion_unavailable',missing_feature='missing_B',
            missing_reason=next(r['reason'] for r in gallery.ab.missing_b if r['image_id']==identity),
            available_features=['a','c1','c2'])
        return result
    i=gallery.positions[identity]
    raw=component_distances({k:gallery.vectors[k][i] for k in KINDS},gallery.vectors)
    normalized,total=combine(raw,params,weights)
    result['ranked_candidate_count']=result['candidate_count']
    for mode in MODES:
        scores=total if mode=='fusion' else raw[mode]
        for rank,j in enumerate(rank_indices(gallery.ids,scores,identity,top_k),1):
            entry=gallery.by_id[gallery.ids[j]]
            result['modes'][mode].append(dict(mode=mode,rank=rank,image_id=entry['image_id'],filename=entry['filename'],
                source=entry['source'],score=float(scores[j]),
                **{'distance_'+k:float(raw[k][j]) for k in KINDS},
                **{'normalized_'+k:float(normalized[k][j]) for k in KINDS},D=float(total[j]),
                **{k+'_row_index':entry['vector_rows'][k] for k in KINDS}))
    return result


def render(gallery,result,path):
    # Fixed 5 x (query + Top-5). CSV/JSON retain all Top-K when K>5.
    canvas=np.full((40+5*320,6*256,3),250,np.uint8)
    title='FOUR-FEATURE FUSION / '+result['weight_configuration']+' / anatomy provisional'
    cv2.putText(canvas,title,(8,26),0,.58,(20,20,20),1,cv2.LINE_AA)
    if result['status']!='ok':
        cv2.putText(canvas,'fusion_unavailable: missing_B; no zero-fill or weight redistribution',(12,35),0,.62,(0,0,170),1,cv2.LINE_AA)
    for row,mode in enumerate(MODES):
        entries=[dict(result['query'],rank=0)]+result['modes'][mode][:5]
        for col,entry in enumerate(entries):
            source=gallery.by_id[entry['image_id']]
            if digest(source['image_path'])!=source['image_sha256']: raise ValueError('Image changed while rendering')
            pixels=cv2.imread(source['image_path'],cv2.IMREAD_UNCHANGED)
            if pixels is None or pixels.shape!=(256,256,3): raise ValueError('Unexpected source image')
            x,y=col*256,40+row*320
            canvas[y:y+256,x:x+256]=pixels
            label=mode.upper()+(' QUERY' if col==0 else ' #'+str(entry['rank']))
            cv2.putText(canvas,label,(x+5,y+273),0,.43,(20,20,20),1,cv2.LINE_AA)
            cv2.putText(canvas,entry['filename'],(x+5,y+291),0,.4,(20,20,20),1,cv2.LINE_AA)
            if col: cv2.putText(canvas,f"d={entry['score']:.10f}",(x+5,y+310),0,.43,(20,20,20),1,cv2.LINE_AA)
    if not cv2.imwrite(str(path),canvas): raise OSError('PNG write failed')


def save_run(gallery,result,directory):
    directory=Path(directory).resolve()
    queries=(OUT/'queries').resolve()
    if queries not in directory.parents:
        raise ValueError('--output must be a new directory under '+str(queries))
    if directory.exists(): raise FileExistsError('Output exists; choose a fresh --output')
    directory.mkdir(parents=True)
    rows=[r for mode in MODES for r in result['modes'][mode]]
    # Explicit header remains available for fusion_unavailable (zero result rows).
    from retrieval.search_ab import write_csv
    write_csv(directory/'results.csv',rows,FIELDS)
    write_json(directory/'results.json',result)
    render(gallery,result,directory/'comparison.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True);parser.add_argument('--top-k',type=int,default=5)
    for kind in KINDS: parser.add_argument('--weight-'+kind,type=float,default=.25)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    weights=tuple(getattr(args,'weight_'+k) for k in KINDS)
    validate_weights(weights)
    gallery=FourGallery();params=load_calibration(gallery)
    result=search(gallery,params,args.image,args.top_k,weights)
    out=args.output or OUT/'queries'/result['query']['image_id']
    save_run(gallery,result,out)
    print('status:',result['status'],'candidate_count:',result['candidate_count'],
          'self_exclusion_count:',result['self_exclusion_count'],'ranked:',result['ranked_candidate_count'])
    for mode,rows in result['modes'].items():
        print(mode.upper())
        for r in rows: print(r['rank'],r['filename'],f"d={r['score']:.12f}")
    if result['status']!='ok': print('missing_B:',result['missing_reason'])
    print('Saved CSV/JSON/PNG:',out)


if __name__=='__main__':main()
