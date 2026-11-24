"""Independent scalar arithmetic; deliberately imports no production retrieval code."""
import csv
import math
from pathlib import Path

import numpy as np

KINDS=('a','b','c1','c2')


def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def load_vectors(root):
    # Read source artifact metadata directly, not the production joined gallery.
    locations={
        'a':('outputs/A_geometry/features_report_v2','features_A_normalized.npy','metadata.csv','a_row_index'),
        'b':('outputs/B_color/color_features_report_v2','features_B_normalized.npy','feature_rows.csv','feature_row_index'),
        'c1':('outputs/C1_lbp/full_v04','features_C1.npy','feature_rows.csv','feature_row_index'),
        'c2':('outputs/C2_hog/full_v1','features_C2.npy','feature_rows.csv','feature_row_index')}
    result={}
    for kind,(folder,array,metadata,index) in locations.items():
        matrix=np.load(root/folder/array,allow_pickle=False)
        result[kind]={r['image_id']:matrix[int(r[index])] for r in rows(root/folder/metadata)}
    return result


def euclidean(left,right):
    return math.sqrt(math.fsum((float(x)-float(y))**2 for x,y in zip(left,right,strict=True)))


def chi_square(left,right,epsilon=1e-8):
    return .5*math.fsum((float(x)-float(y))**2/(float(x)+float(y)+epsilon)
                        for x,y in zip(left,right,strict=True))


def distances(vectors,left,right):
    return {kind:(chi_square if kind=='c1' else euclidean)(vectors[kind][left],vectors[kind][right])
            for kind in KINDS}


def median(values):
    ordered=sorted(values)
    n=len(ordered)
    if not n:raise ValueError('Empty median')
    return ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2


def fusion(raw,medians,weights,epsilon=1e-8):
    return math.fsum(float(weights[i])*raw[kind]/(medians[kind]+epsilon) for i,kind in enumerate(KINDS))


def ranking(vectors,ids,query,medians,weights=(.25,.25,.25,.25)):
    values={key:distances(vectors,query,key) for key in ids if key!=query}
    scores={key:fusion(raw,medians,weights) for key,raw in values.items()}
    order={kind:sorted(values,key=lambda key:(values[key][kind],key)) for kind in KINDS}
    order['fusion']=sorted(values,key=lambda key:(scores[key],key))
    return values,scores,order
