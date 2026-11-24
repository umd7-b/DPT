"""A audit: arithmetic, artifact lineage, epsilon sensitivity and real images."""
from common import *
import ast
import contextlib
import io

import cv2
from features.A_geometry.src import geometry_features as impl

A = ROOT / 'outputs/A_geometry/features'
raw = np.load(A/'features_A_raw.npy', allow_pickle=False)
z = np.load(A/'features_A_normalized.npy', allow_pickle=False)
with np.load(A/'geometry_stats.npz', allow_pickle=False) as file:
    stats = {key: file[key].copy() for key in file.files}
rows = read(A/'metadata.csv')
x = raw.astype(np.float64)
# Independent reduction per dimension, using scalar compensated sums.
means = np.array([math.fsum(map(float, column))/len(column) for column in x.T])
sigmas = np.array([math.sqrt(math.fsum((float(v)-mu)**2 for v in column)/len(column))
                   for mu, column in zip(means, x.T)])
safe = np.where(sigmas < 1e-8, 1., sigmas)
oracle = (x-means)/safe
np.testing.assert_allclose(stats['mean'], means, rtol=0, atol=1e-12)
np.testing.assert_allclose(stats['std'], safe, rtol=0, atol=1e-12)
# Exact reproduction of the actual implementation's NumPy reduction/cast.
implemented = ((x-x.mean(axis=0))/np.where(x.std(axis=0)<1e-8, 1., x.std(axis=0))).astype(np.float32)
assert np.array_equal(z, implemented)
epsilon_records = []
dimension_records = []
for epsilon in (1e-12, 1e-8, 1e-6):
    report = (x-stats['mean'])/(x.std(axis=0)+epsilon)
    implemented64 = (x-stats['mean'])/stats['std']
    unequal = report != implemented64
    changed32 = report.astype(np.float32) != z
    delta = np.abs(report-implemented64)
    epsilon_records.append(dict(epsilon=epsilon, epsilon_status='illustrative choice; PDF does not fix value',
        affected_dimensions=int(np.any(unequal, axis=0).sum()), affected_images=int(np.any(unequal, axis=1).sum()),
        affected_values=int(unequal.sum()), changed_float32_values=int(changed32.sum()),
        changed_float32_dimensions=int(np.any(changed32, axis=0).sum()),
        max_absolute_difference=float(delta.max()), mean_absolute_difference=float(delta.mean())))
    if epsilon == 1e-8:
        for j in range(150):
            dimension_records.append(dict(index=j, mean=float(stats['mean'][j]), sigma=float(x.std(axis=0)[j]),
                saved_divisor=float(stats['std'][j]), pdf_divisor_if_epsilon_1e8=float(x.std(axis=0)[j]+epsilon),
                affected_values=int(unequal[:, j].sum()), changed_float32_values=int(changed32[:, j].sum()),
                max_difference=float(delta[:, j].max())))
csv_out('a_zscore_dimensions.csv', dimension_records)
csv_out('a_zscore_epsilon_sensitivity.csv', epsilon_records)

real = []
detail = []
for name in ('cfd_final_00001.png', 'cfd_final_00069.png', 'cfd_final_00088.png', 'cfd_final_00144.png'):
    p = impl.detect_landmarks(DATA/'images'/name)  # Audit inference; never invokes a writer.
    np.save(EVIDENCE/(Path(name).stem+'_landmarks68.npy'), p, allow_pickle=False)
    actual = impl.calculate_ratios(p)
    expected, operands, centers = scalar_a2(p)
    ratios_without_guard, _, _ = scalar_a2(p, epsilon=0.)
    np.testing.assert_allclose(actual, expected, rtol=2e-6, atol=2e-5)
    normalized, distance = impl.normalize_landmarks(p)
    center64 = np.array(centers[2])
    landmark_oracle = (p.astype(np.float64)-center64)/centers[3]
    np.testing.assert_allclose(normalized, landmark_oracle, rtol=2e-6, atol=2e-6)
    vector = np.r_[normalized.flatten().astype(np.float32), actual]
    i = next(i for i, r in enumerate(rows) if r['image_name'] == name)
    max_raw_error = float(np.max(np.abs(vector-raw[i])))
    real.append(dict(image_name=name, max_raw_error=max_raw_error,
                     max_coordinate_oracle_error=float(np.max(np.abs(normalized-landmark_oracle))),
                     max_a2_oracle_error=float(np.max(np.abs(actual-expected))), eye_distance=float(distance)))
    for j in range(14):
        detail.append(dict(image_name=name, a2_index=j+1, feature_name=impl.FEATURE_NAMES[j],
            numerator=operands[j][0], denominator_before_epsilon=operands[j][1],
            denominator_epsilon=1e-8 if j<13 else 0., unit='degrees' if j==13 else 'dimensionless',
            code_value=float(actual[j]), independent_scalar_value=expected[j],
            ratio_without_guard=ratios_without_guard[j], absolute_error=abs(float(actual[j])-expected[j])))
    thumb = cv2.resize(cv2.imread(str(DATA/'images'/name)), (768, 768))
    for k, (px, py) in enumerate(p):
        loc = (int(round(float(px)*3)), int(round(float(py)*3)))
        cv2.circle(thumb, loc, 3, (0, 0, 255), -1)
        cv2.putText(thumb, str(k), (loc[0]+3, loc[1]-3), 0, .38, (0, 200, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(EVIDENCE/(Path(name).stem+'_68_annotated.png')), thumb)
csv_out('a2_real_image_oracles.csv', detail)
csv_out('landmark_mapping.csv', [dict(index68=i, index478=mp, x_first_image=float(np.load(EVIDENCE/'cfd_final_00001_landmarks68.npy')[i,0]),
     y_first_image=float(np.load(EVIDENCE/'cfd_final_00001_landmarks68.npy')[i,1])) for i, mp in enumerate(impl.INDICES)])

# A-only legacy query recomputation, read-only: do not call main(), which writes a preview.
from retrieval import search_geometry
p = np.load(EVIDENCE/'cfd_final_00144_landmarks68.npy')
coords, _ = impl.normalize_landmarks(p)
qraw = np.r_[coords.flatten().astype(np.float32), impl.calculate_ratios(p)]
qz = (qraw.astype(np.float64)-stats['mean'])/stats['std']
dist = np.linalg.norm(z.astype(np.float64)-qz, axis=1)
for i,r in enumerate(rows):
    if Path(r['image_path']).resolve() == search_geometry.QUERY_IMAGE.resolve():
        dist[i] = np.inf
legacy_top = [dict(rank=n, image_name=rows[i]['image_name'], distance=float(dist[i]))
              for n,i in enumerate(np.argsort(dist)[:5],1)]
csv_out('a_only_legacy_recomputed_top5.csv', legacy_top)
legacy_path = ROOT/'outputs/retrieval/search_results/cfd_final_00144_top5.png'
legacy_png = dict(path=str(legacy_path), exists=legacy_path.exists(),
                  limitation='Legacy output stores a PNG only; no machine-readable historical distances')
if legacy_path.exists():
    canvas = np.full((310, 256*6, 3), 255, np.uint8)
    canvas[:256,:256] = cv2.resize(cv2.imread(str(search_geometry.QUERY_IMAGE)), (256,256))
    cv2.putText(canvas, 'QUERY', (80,280), cv2.FONT_HERSHEY_SIMPLEX, .65, (0,0,0), 2)
    for rank, index in enumerate(np.argsort(dist)[:5], 1):
        image = cv2.imread(rows[index]['image_path'])
        xoff = rank*256
        canvas[:256,xoff:xoff+256] = cv2.resize(image,(256,256))
        cv2.putText(canvas,f'TOP {rank}',(xoff+75,275),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,0),2)
        cv2.putText(canvas,f'D={dist[index]:.3f}',(xoff+65,300),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1)
    stored = cv2.imread(str(legacy_path))
    legacy_png['exact_decoded_pixel_reproduction'] = bool(np.array_equal(canvas, stored))
    cv2.imwrite(str(EVIDENCE/'a_only_legacy_reconstructed.png'),canvas)

legacy_all = []
for stored_path in sorted((ROOT/'outputs/retrieval/search_results').glob('*_top5.png')):
    name = stored_path.name.replace('_top5.png','.png')
    p = np.load(EVIDENCE/(Path(name).stem+'_landmarks68.npy'),allow_pickle=False)
    coords,_ = impl.normalize_landmarks(p)
    qraw = np.r_[coords.flatten().astype(np.float32),impl.calculate_ratios(p)]
    qz = (qraw.astype(np.float64)-stats['mean'])/stats['std']
    distances = np.linalg.norm(z.astype(np.float64)-qz,axis=1)
    for i,row in enumerate(rows):
        if row['image_name']==name:distances[i]=np.inf
    selected=np.argsort(distances)[:5]
    found=[dict(rank=n,image_name=rows[i]['image_name'],distance=float(distances[i])) for n,i in enumerate(selected,1)]
    csv_out(Path(name).stem+'_a_only_top5_recomputed.csv',found)
    canvas=np.full((310,256*6,3),255,np.uint8)
    canvas[:256,:256]=cv2.resize(cv2.imread(str(DATA/'images'/name)),(256,256))
    cv2.putText(canvas,'QUERY',(80,280),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),2)
    for rank,index in enumerate(selected,1):
        xoff=rank*256
        canvas[:256,xoff:xoff+256]=cv2.resize(cv2.imread(rows[index]['image_path']),(256,256))
        cv2.putText(canvas,f'TOP {rank}',(xoff+75,275),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,0,0),2)
        cv2.putText(canvas,f'D={distances[index]:.3f}',(xoff+65,300),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1)
    legacy_all.append(dict(image_name=name,path=str(stored_path),exact_decoded_pixel_reproduction=bool(np.array_equal(canvas,cv2.imread(str(stored_path)))),top5=found))

summary = dict(raw_shape=list(raw.shape), raw_dtype=str(raw.dtype), z_dtype=str(z.dtype),
    metadata_count=len(rows), finite=bool(np.isfinite(x).all() and np.isfinite(z).all()),
    mean_oracle_max_error=float(np.max(abs(means-stats['mean']))),
    std_oracle_max_error=float(np.max(abs(safe-stats['std']))),
    normalized_artifact_exactly_reproduced=bool(np.array_equal(z, implemented)),
    safe_dimensions=np.flatnonzero(sigmas<1e-8).tolist(), zero_sigma_dimensions=np.flatnonzero(sigmas==0).tolist(),
    epsilon_in_normalizer=None, epsilon_in_a2=1e-8, epsilon_sensitivity=epsilon_records,
    real_images=real, legacy_top5=legacy_top, legacy_png=legacy_png,legacy_all_previews=legacy_all,
    note='Arithmetic verification does not certify anatomical endpoints or PDF compliance')
dump('a_verification.json', summary)
print(json.dumps(summary,indent=2))
