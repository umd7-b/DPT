"""Independent saved-data verification; no extractor, fitting or ranking helper calls."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import ROOT, A_METADATA, read_csv, digest


def verify(gallery):
    gallery = Path(gallery).resolve()
    for name,expected in json.loads((gallery/'gallery_integrity.json').read_text()).items():
        path=(gallery/name).resolve()
        if gallery not in path.parents or digest(path)!=expected:raise ValueError('Gallery integrity mismatch')
    manifest = read_csv(gallery/'manifest.csv'); valid = read_csv(gallery/'feature_rows.csv')
    fit = read_csv(gallery/'fit_manifest.csv'); metadata = read_csv(A_METADATA)
    if len(manifest)!=1438 or [r['image_name'] for r in manifest]!=[r['image_name'] for r in metadata]:
        raise ValueError('Full metadata order/count mismatch')
    expected_valid = [r for r in manifest if r['status']=='valid']
    if expected_valid != valid:raise ValueError('Compact valid manifest mismatch')
    if [int(r['feature_row_index']) for r in valid]!=list(range(len(valid))):raise ValueError('Noncontiguous feature rows')
    if [r['image_id'] for r in fit]!=[r['image_id'] for r in valid]:raise ValueError('Fit identities mismatch')
    missing = [r for r in manifest if r['status']!='valid']
    if read_csv(gallery/'missing_features.csv')!=missing:raise ValueError('Missing-data manifest mismatch')
    mask_count = 0
    for row in manifest:
        if row['input_verified']!='True':raise ValueError('Unverified input in gallery manifest')
        if digest(Path(row['image_path']))!=row['source_sha256']:raise ValueError('Source image changed')
        masks = []
        for region in ('skin','hair'):
            path = Path(row[region+'_mask_path'])
            if digest(path)!=row[region+'_mask_sha256']:raise ValueError('Raw mask changed')
            mask = cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
            if mask is None or mask.shape!=(256,256) or mask.dtype!=np.uint8 or not set(np.unique(mask)).issubset({0,255}):
                raise ValueError('Invalid raw mask format')
            if int(np.count_nonzero(mask))!=int(row[region+'_pixels']):raise ValueError('Mask count mismatch')
            masks.append(mask);mask_count+=1
        if np.any((masks[0]>0)&(masks[1]>0)):raise ValueError('Mask overlap')
        enough = all(int(row[r+'_pixels'])>=100 for r in ('skin','hair'))
        if enough != (row['status']=='valid'):raise ValueError('Missing-region policy mismatch')
        if not enough and row['feature_row_index']!='':raise ValueError('Missing row has fake feature index')
    x=np.load(gallery/'features_B_raw.npy',allow_pickle=False)
    z=np.load(gallery/'features_B_normalized.npy',allow_pickle=False)
    if x.shape!=(len(valid),144) or z.shape!=x.shape or x.dtype!=np.float64 or z.dtype!=np.float64 or not np.isfinite(x).all() or not np.isfinite(z).all():
        raise ValueError('Invalid saved B144 matrices')
    histogram_errors=[]
    for a,b in ((0,48),(60,70),(72,120),(132,142)):
        for h in x[:,a:b]:
            if min(h)<0:raise ValueError('Negative raw histogram')
            histogram_errors.append(abs(math.fsum(float(v) for v in h)-1))
    if max(histogram_errors)>1e-12:raise ValueError('Histogram L1 mismatch')
    if np.any(x[:,[70,71,142,143]]<0) or np.any(x[:,[70,71,142,143]]>1):raise ValueError('Circular range mismatch')
    n=len(valid)
    means=np.array([math.fsum(float(v) for v in col)/n for col in x.T])
    raw_stds=np.array([math.sqrt(math.fsum((float(v)-mu)**2 for v in col)/n) for col,mu in zip(x.T,means)])
    div=np.array([1 if std<1e-8 else std for std in raw_stds])
    with np.load(gallery/'normalization_stats.npz',allow_pickle=False) as f:
        saved_mean=f['mean'].copy();saved_std=f['std'].copy()
        np.testing.assert_allclose(saved_mean,means,atol=1e-11,rtol=1e-12)
        np.testing.assert_allclose(saved_std,div,atol=1e-11,rtol=1e-12)
        np.testing.assert_allclose(f['raw_std'],raw_stds,atol=1e-11,rtol=1e-12)
        np.testing.assert_array_equal(f['constant_dimensions'],np.flatnonzero(raw_stds<1e-8))
        if int(f['fit_count'])!=n or str(f['fit_manifest_sha256'])!=digest(gallery/'fit_manifest.csv'):
            raise ValueError('Fit provenance mismatch')
    expected=(x-means)/div
    np.testing.assert_allclose(z,expected,atol=1e-10,rtol=1e-10)
    np.testing.assert_array_equal(z,(x-saved_mean)/saved_std)
    old=ROOT/'outputs/B_color/color_features_100/A_skin1_hair17_raw'
    old_x=np.load(old/'features_B_unscaled.npy',allow_pickle=False)
    old_rows=read_csv(old/'feature_rows.csv'); index={r['image_name']:i for i,r in enumerate(valid)}
    for i,row in enumerate(old_rows):np.testing.assert_array_equal(old_x[i],x[index[row['image_name']]])
    rankings=read_csv(gallery/'retrieval/top5.csv'); grouped=defaultdict(list)
    for row in rankings:grouped[row['query_id']].append(row)
    if len(grouped)!=10 or len(rankings)!=50:raise ValueError('Expected 10 queries and 50 results')
    id_index={r['image_id']:i for i,r in enumerate(valid)}; distance_error=0.
    for q,found in grouped.items():
        qi=id_index[q]
        independent=sorted((math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(z[qi],z[i]))),r['image_name'],r['image_id'])
                           for i,r in enumerate(valid) if r['image_id']!=q)[:5]
        for actual,(distance,name,identity) in zip(found,independent):
            if actual['image_id']!=identity or actual['image_name']!=name or actual['query_id']==actual['image_id']:
                raise ValueError('Independent Euclidean Top-5/identity mismatch')
            error=abs(float(actual['distance'])-distance)
            if error>1e-10:raise ValueError('Euclidean distance mismatch')
            distance_error=max(distance_error,error)
    summary=dict(images=len(manifest),valid_vectors=n,missing_vectors=len(missing),shape=list(x.shape),
        source_images_hash_verified=len(manifest),raw_masks_verified=mask_count,
        histogram_checks=len(histogram_errors),max_independent_histogram_l1_error=max(histogram_errors),
        max_independent_mean_error=float(np.max(np.abs(saved_mean-means))),
        max_independent_std_error=float(np.max(np.abs(saved_std-div))),
        max_independent_z_error=float(np.max(np.abs(z-expected))),
        saved_stats_reconstruction_error=float(np.max(np.abs(z-(x-saved_mean)/saved_std))),
        legacy_raw100_vectors_unchanged=len(old_rows),independent_rank_rows=len(rankings),
        max_independent_distance_error=distance_error,zero_or_near_zero_dimensions=np.flatnonzero(raw_stds<1e-8).tolist(),
        nan_count=int(np.isnan(x).sum()+np.isnan(z).sum()),inf_count=int(np.isinf(x).sum()+np.isinf(z).sum()),
        semantic_quality='Not evaluated without independent labels',new_inferences=0)
    output=gallery/'validation/independent_validation.json'
    if output.exists():
        if json.loads(output.read_text(encoding='utf-8'))!=summary:
            raise ValueError('Existing independent validation differs; preserving original evidence')
    else:
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--gallery',type=Path,default=ROOT/'outputs/B_color/color_features_full_v1')
    args=cli.parse_args();print(json.dumps(verify(args.gallery),indent=2))


if __name__=='__main__':main()
