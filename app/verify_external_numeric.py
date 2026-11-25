"""Independent scalar checks of actual new query vectors (never refits statistics)."""
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np

from app.server import PortraitService
from app.external_config import QA_EVIDENCE
from features.C1_lbp.src.full_v04 import V04Context
from features.C1_lbp.src.lbp236 import REGIONS
from features.C1_lbp.verification import scalar_oracle as lbp
from features.C2_hog.verification import scalar_oracle as hog
from retrieval import fusion_oracle as distance

ROOT=Path(__file__).resolve().parents[1]
E=QA_EVIDENCE

def load(path):return np.load(path,allow_pickle=False)

def verify(image,folder,result,gallery):
    bgr=cv2.imread(str(image));points=load(folder/'landmarks478.npy')
    vectors={k:load(folder/n) for k,n in dict(a='query_A_normalized.npy',b='query_B_normalized.npy',c1='query_C1.npy',c2='query_C2.npy').items()}
    a=load(ROOT/'outputs/A_geometry/features_report_v2/normalization_stats.npz')
    raw=load(folder/'query_A_raw.npy')
    av=np.array([(float(raw[i])-float(a['mean'][i]))/(float(a['raw_sigma'][i])+1e-8) for i in range(150)])
    ms=load(ROOT/'outputs/B_color/color_features_report_v2/moment_normalization_stats.npz')
    fs=load(ROOT/'outputs/B_color/color_features_report_v2/final_normalization_stats.npz')
    br=load(folder/'query_B_raw.npy');after=br.copy()
    for j,i in enumerate([*range(48,60),*range(120,132)]):
        sigma=float(ms['raw_sigma'][j]);after[i]=(float(br[i])-float(ms['mean'][j]))/(1. if sigma<1e-8 else sigma)
    bv=np.array([(float(after[i])-float(fs['mean'][i]))/(1. if float(fs['raw_sigma'][i])<1e-8 else float(fs['raw_sigma'][i])) for i in range(144)])
    np.testing.assert_array_equal(av,vectors['a']);np.testing.assert_array_equal(after,load(folder/'query_B_after_moments.npy'));np.testing.assert_array_equal(bv,vectors['b'])
    gray=lbp.gray_image(bgr);polygons=V04Context().polygons(points);hist=[];counts=[];centres={}
    for name in REGIONS:
        # Full image polygon scan and explicit21 support, independent scalar LBP.
        mask=lbp.mask_from_vertices(polygons[name]);n,h,selected=lbp.histogram(gray,mask)
        counts.append(n);hist.extend(h);centres[name]=len(selected)
    cv=np.array(hist,np.float64);hv=hog.extract(bgr)['vector']
    np.testing.assert_array_equal(cv,vectors['c1']);np.testing.assert_array_equal(np.array(counts),load(folder/'counts_C1.npy'))
    np.testing.assert_allclose(hv,vectors['c2'],rtol=0,atol=1e-14)
    medians=result['medians'];weights=[result['weights'][k] for k in ('a','b','c1','c2')]
    rows=[]
    for i,key in enumerate(gallery.ids):
        raw={k:(distance.chi_square if k=='c1' else distance.euclidean)(vectors[k],gallery.vectors[k][i]) for k in vectors}
        score=sum(weights[j]*raw[k]/(medians[k]+1e-8) for j,k in enumerate(('a','b','c1','c2')))
        rows.append((key,raw,score))
    maximum=0.
    for mode in ('a','b','c1','c2','fusion'):
        ordered=sorted(rows,key=lambda r:((r[2] if mode=='fusion' else r[1][mode]),r[0]))[:5]
        assert [r[0] for r in ordered]==[r['image_id'] for r in result['modes'][mode]]
        for (key,raw,d),observed in zip(ordered,result['modes'][mode]):
            for k in vectors:
                maximum=max(maximum,abs(raw[k]-observed['distance_'+k]))
                assert math.isclose(raw[k],observed['distance_'+k],rel_tol=1e-14,abs_tol=1e-14)
                assert math.isclose(raw[k]/(medians[k]+1e-8),observed['normalized_'+k],rel_tol=1e-14,abs_tol=1e-14)
            assert math.isclose(d,observed['D'],rel_tol=1e-14,abs_tol=1e-14)
    return dict(shapes={k:list(v.shape) for k,v in vectors.items()},dtypes={k:str(v.dtype) for k,v in vectors.items()},
        oracle_max_abs=dict(a=float(abs(av-vectors['a']).max()),b=float(abs(bv-vectors['b']).max()),c1=float(abs(cv-vectors['c1']).max()),c2=float(abs(hv-vectors['c2']).max())),
        L1=vectors['c1'].reshape(4,59).sum(axis=1).tolist(),eligible_centres=centres,counts_exact=True,scalar_candidates=len(rows),
        five_rankings_exact=True,max_distance_error=maximum,pixel_sha256=hashlib.sha256(bgr.tobytes()).hexdigest())

def main():
    service=PortraitService()
    try:
        full=json.loads((E/'real_query_verification.json').read_text('utf8'))
        cropped=json.loads((E/'browser_query_result.json').read_text('utf8'))
        revision=cropped['query']['image_url'].split('revision=')[1]
        results=dict(reencoded=verify(E/'fixtures/reencoded.png',Path(full['features_directory']),full['query']['result'],service.gallery),
            manual_crop=verify(E/('browser_query/crop_'+revision+'.png'),E/('browser_query/features_'+revision),cropped,service.gallery))
        (E/'numerical_verification.json').write_text(json.dumps(dict(status='PASS',results=results),indent=2),encoding='utf8')
        print(json.dumps(results,indent=2))
    finally:service.external.close()

if __name__=='__main__':main()
