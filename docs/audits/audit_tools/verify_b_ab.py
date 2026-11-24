"""Independent artifact and retrieval audit, without invoking output-writing APIs."""
from common import *
from collections import Counter
import cv2
import bisect
import random

B=ROOT/'outputs/B_color/color_features_full_v1'
A=ROOT/'outputs/A_geometry/features'
AB=ROOT/'outputs/retrieval/ab_experiment'
brows=read(B/'feature_rows.csv'); manifest=read(B/'manifest.csv')
arows=read(A/'metadata.csv')
raw=np.load(B/'features_B_raw.npy',allow_pickle=False)
z=np.load(B/'features_B_normalized.npy',allow_pickle=False)
av=np.load(A/'features_A_normalized.npy',allow_pickle=False).astype(np.float64)
with np.load(B/'normalization_stats.npz',allow_pickle=False) as file:
    stats={k:file[k].copy() for k in file.files}
integrity=json.loads((B/'gallery_integrity.json').read_text(encoding='utf-8'))
assert all(sha(B/name)==value for name,value in integrity.items())
assert json.loads((B/'schema.json').read_text(encoding='utf-8'))['id']=='B144_raw_v1.0.0'
assert int(stats['fit_count'])==len(brows) and str(stats['profile'])=='all144'
assert str(stats['schema_id'])=='B144_raw_v1.0.0'
assert [r['image_name'] for r in manifest]==[r['image_name'] for r in arows]
assert len({r['image_id'] for r in manifest})==len(manifest)
assert [r for r in manifest if r['status']=='valid']==brows
assert all(arows[int(row['a_row_index'])]['image_name']==row['image_name'] and
           int(row['feature_row_index'])==i for i,row in enumerate(brows))
means=np.array([math.fsum(map(float,col))/len(raw) for col in raw.T])
sigmas=np.array([math.sqrt(math.fsum((float(v)-mu)**2 for v in col)/len(raw)) for col,mu in zip(raw.T,means)])
np.testing.assert_allclose(means,stats['mean'],rtol=0,atol=1e-12)
np.testing.assert_allclose(sigmas,stats['raw_std'],rtol=0,atol=1e-12)
oracle=(raw-means)/np.where(sigmas<1e-8,1.,sigmas)
np.testing.assert_allclose(z,oracle,rtol=0,atol=1e-12)
assert np.array_equal(z,(raw-stats['mean'])/stats['std'])
assert sha(B/'fit_manifest.csv')==str(stats['fit_manifest_sha256'])
assert raw.shape==z.shape==(1437,144)
assert np.isfinite(raw).all() and np.isfinite(z).all()
circular=raw[:,[70,71,142,143]]
assert np.all((circular>=0)&(circular<=1))
fullmask=0; histogram_errors=[]; selected_errors=[]; details=[]
special={'cfd_final_00001','cfd_final_00069','cfd_final_00144','cfd_final_00239','hf_merged_00209',
         'hf_merged_00676','hf_merged_00694','hf_merged_00722','hf_merged_00683','hf_merged_00102'}
byid={r['image_id']:r for r in brows}
for n,row in enumerate(manifest):
    name=row['image_name']; identity=row['image_id']
    assert sha(Path(row['image_path']))==row['source_sha256']
    image=cv2.imread(row['image_path'])
    masks={}
    receipt=json.loads((ROOT/'outputs/B_color/uniface_full/receipts'/f'{identity}.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'outputs/B_color/uniface_full/receipts'/f'{identity}.json')==row['receipt_sha256']
    for region,offset in [('skin',0),('hair',72)]:
        path=Path(row[region+'_mask_path'])
        assert sha(path)==row[region+'_mask_sha256']==receipt['artifacts'][f'masks/{region}/{identity}_{region}_mask.png']
        mask=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
        assert mask.shape==(256,256) and mask.dtype==np.uint8 and set(np.unique(mask)) <= {0,255}
        assert int(np.count_nonzero(mask))==int(row[region+'_pixels'])
        fullmask+=1; masks[region]=mask
        if identity in byid:
            pixels=image[mask>0]
            hsv=cv2.cvtColor(pixels.reshape(-1,1,3),cv2.COLOR_BGR2HSV).reshape(-1,3)
            hs=np.bincount((hsv[:,0].astype(int)//15)*4+hsv[:,1].astype(int)//64,minlength=48)/len(pixels)
            hh=np.bincount(hsv[:,0].astype(int)//18,minlength=10)/len(pixels)
            fi=int(byid[identity]['feature_row_index'])
            histogram_errors.extend([float(np.max(abs(raw[fi,offset:offset+48]-hs))),
                                     float(np.max(abs(raw[fi,offset+60:offset+70]-hh)))])
            if identity in special:
                expected=scalar_color(image,mask)
                delta=float(np.max(abs(raw[fi,offset:offset+72]-expected)))
                assert delta<1e-10
                selected_errors.append(delta)
                for j,(actual,wanted) in enumerate(zip(raw[fi,offset:offset+72],expected)):
                    details.append(dict(image_id=identity,region=region,region_index=j,
                                        actual=float(actual),oracle=float(wanted),absolute_error=abs(float(actual)-float(wanted))))
    assert not np.any((masks['skin']>0)&(masks['hair']>0))
csv_out('b_selected_descriptor_oracles.csv',details)
top=read(B/'retrieval/top5.csv')
distance_errors=[]
for query in sorted({r['query_id'] for r in top}):
    qi=int(byid[query]['feature_row_index'])
    # Scalar fsum L2 oracle, not rank() or np.linalg.norm().
    distances=[math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(v,z[qi]))) for v in z]
    ordered=sorted((i for i,r in enumerate(brows) if r['image_id']!=query),
                   key=lambda i:(distances[i],brows[i]['image_name']))[:5]
    saved=sorted([r for r in top if r['query_id']==query],key=lambda r:int(r['rank']))
    assert [brows[i]['image_id'] for i in ordered]==[r['image_id'] for r in saved]
    distance_errors.extend(abs(distances[i]-float(r['distance'])) for i,r in zip(ordered,saved))

params=json.loads((AB/'calibration/median_params.json').read_text(encoding='utf-8'))
pairs=read(AB/'calibration/representative_pairs.csv')
sample_ids=params['image_ids']
n=len(sample_ids)
starts=[i*(2*n-i-1)//2 for i in range(n-1)]
pair_ranks=sorted(random.Random(params['seed']).sample(range(n*(n-1)//2),params['pair_count']))
expected_pairs=[]
for rank in pair_ranks:
    i=bisect.bisect_right(starts,rank)-1
    j=i+1+rank-starts[i]
    expected_pairs.append((sample_ids[i],sample_ids[j]))
assert expected_pairs==[(r['image_id_1'],r['image_id_2']) for r in pairs]
ai={Path(r['image_name']).stem:i for i,r in enumerate(arows)}
bi={r['image_id']:int(r['feature_row_index']) for r in brows}
calib=[]
for row in pairs:
    i,j=row['image_id_1'],row['image_id_2']
    da=math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(av[ai[i]],av[ai[j]])))
    db=math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(z[bi[i]],z[bi[j]])))
    assert abs(da-float(row['distance_a']))<1e-12 and abs(db-float(row['distance_b']))<1e-12
    calib.append((da,db))
medians=np.median(calib,axis=0)
assert np.max(abs(medians-[params['median_a'],params['median_b']]))<1e-12
assert all(sha(Path(name))==value for name,value in params['fingerprint'].items())
query=json.loads((AB/'queries/cfd_final_00001/results.json').read_text(encoding='utf-8'))
ids=sorted(bi)
qa,qb=av[ai['cfd_final_00001']],z[bi['cfd_final_00001']]
da=np.array([math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(av[ai[key]],qa))) for key in ids])
db=np.array([math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(z[bi[key]],qb))) for key in ids])
na,nb=da/(params['median_a']+params['epsilon']),db/(params['median_b']+params['epsilon'])
for mode,scores in [('ab',.5*na+.5*nb),('a_only',na),('b_only',nb)]:
    indices=sorted((i for i,key in enumerate(ids) if key!='cfd_final_00001'),key=lambda i:(scores[i],ids[i]))[:5]
    assert [ids[i] for i in indices]==[r['image_id'] for r in query['results'][mode]]
missing=read(B/'missing_features.csv')
assert len(missing)==1 and missing[0]['image_id']=='hf_merged_00209'
missing_query=json.loads((AB/'queries/hf_merged_00209/results.json').read_text(encoding='utf-8'))
assert missing_query['status']=='missing_B' and not missing_query['results']['ab'] and not missing_query['results']['b_only']
# Explicitly mark dependencies in the new audit tree, never mutate old calibration/rankings.
dependency=dict(status='LEGACY_A_NORMALIZATION_NONCONFORMING',reason='A normalizer uses std_safe, not sigma+epsilon',
    must_recalibrate_after_A_fix=True,artifacts=[dict(path=str(path),sha256=sha(path))
        for folder in [AB,ROOT/'outputs/retrieval/search_results',ROOT/'outputs/retrieval/ab_validation']
        for path in sorted(folder.rglob('*')) if path.is_file()],
    a_vector_sha256=sha(A/'features_A_normalized.npy'),a_stats_sha256=sha(A/'geometry_stats.npz'),
    b_normalization_sequence_status='DEVIATION: pre-concatenation moment normalization stage not implemented',
    warning='Reproducibility of these legacy outputs does not certify PDF compliance; do not reuse their median after corrected vectors')
dump('legacy_dependency_register.json',dependency)
summary=dict(raw_shape=list(raw.shape),normalized_shape=list(z.shape),dtype=str(raw.dtype),
    manifest_rows=len(manifest),valid_rows=len(brows),missing=missing,
    integrity_files_checked=len(integrity),raw_mask_files_checked=fullmask,
    histogram_checks=len(histogram_errors),max_histogram_recompute_error=max(histogram_errors),
    circular_raw_min=float(circular.min()),circular_raw_max=float(circular.max()),
    independent_full_descriptor_regions=len(selected_errors),max_descriptor_oracle_error=max(selected_errors),
    mean_oracle_max_error=float(np.max(abs(means-stats['mean']))),std_oracle_max_error=float(np.max(abs(sigmas-stats['raw_std']))),
    z_oracle_max_error=float(np.max(abs(z-oracle))),constant_dimensions=np.flatnonzero(sigmas<1e-8).tolist(),
    b_top5_rows_verified=len(top),max_saved_b_distance_error=max(distance_errors),
    ab_pairs_verified=len(pairs),ab_median_a=float(medians[0]),ab_median_b=float(medians[1]),
    ab_pair_id_selection_independently_reproduced=True,
    ab_top5_all_three_modes_verified=True,ab_missing_query_verified=True,
    normalization_stage_observed='unscaled descriptor -> concatenate B144 -> one Z-score all144',
    warning_count=sum(bool(r['warning']) for r in manifest),
    registered_legacy_artifacts=len(dependency['artifacts']))
dump('b_ab_verification.json',summary)
print(json.dumps({k:v for k,v in summary.items() if k!='missing'},indent=2))
