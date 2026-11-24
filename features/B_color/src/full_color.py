"""Approved B144 v1 full-gallery extraction from existing raw UniFace masks.

The numerical descriptor is reused unchanged. No segmentation is performed.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import platform
import time

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import (
    ROOT, DATASET, UNIFACE, A_METADATA, read_csv, digest, unique_index, load_mask)
from features.B_color.src.color_features import (
    SCHEMA as LEGACY_SCHEMA, feature_names, extract_color, fit_standardizer, transform)
from features.B_color.src.run_color_experiment import save_csv, write_json

DEFAULT_OUTPUT = ROOT/'outputs/B_color/color_features_full_v1'
SCHEMA = deepcopy(LEGACY_SCHEMA)
SCHEMA.update({
    'id':'B144_raw_v1.0.0', 'version':'1.0.0', 'approval_date':'2026-11-22',
    'conventions_status':'APPROVED FOR IMPLEMENTATION by user for D01-D17',
    'authority':'PDF explicit requirements plus user-approved implementation conventions; not all formulas are verbatim PDF',
    'skin_class':1, 'hair_class':17, 'mask_variant':'raw', 'erosion_for_features':False,
    'minimum_region_pixels':100, 'saturation_filter':False,
    'low_saturation_warning':{'threshold':10,'fraction_gt':0.5},
    'normalization':{'profile':'all144','stage':'descriptor, concatenate B144, then one gallery Z-score',
                     'ddof':0,'std_threshold':1e-8,'small_std_divisor':1.,'query_refit':False,
                     'fit_scope':'all valid vectors in the 1438-image gallery'},
    'distance':'Euclidean on Z-score vectors', 'self_match':'exclude by image_id',
    'tie_break':'filename ascending', 'image_id':'metadata image_id if present, otherwise filename stem',
})
FIELDS = ['a_row_index','image_id','image_name','dataset_source','image_path','source_sha256',
          'skin_mask_path','skin_mask_sha256','hair_mask_path','hair_mask_sha256','receipt_sha256',
          'status','reason','feature_row_index','skin_pixels','hair_pixels','skin_status','hair_status',
          'input_verified','skin_low_saturation_fraction','hair_low_saturation_fraction',
          'uniface_warning','warning','processing_time_ms']


def protect_state(dataset, excluded):
    """Hash existing project artifacts and dataset bytes, excluding new output."""
    files = {}
    for folder in ('features','retrieval','src','shared','models','annotations','outputs','docs','tests','scripts'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and excluded not in path.resolve().parents:
                files[str(path.resolve())] = digest(path)
    for path in Path(dataset).rglob('*'):
        if path.is_file():files[str(path.resolve())] = digest(path)
    return files


def new_output(path, protected=()):
    path = Path(path).resolve()
    base = (ROOT/'outputs/B_color').resolve()
    if base not in path.parents:raise ValueError('Use a dedicated outputs/B_color subdirectory')
    for source in protected:
        source = Path(source).resolve()
        if path == source or source in path.parents or path in source.parents:
            raise ValueError('Output overlaps protected input')
    if path.exists() and any(path.iterdir()):raise FileExistsError('Output must be new/empty')
    return path


def verified_input(dataset, uniface, row, metric):
    """Verify image, receipt, raw-mask bytes, dimensions and saved pixel counts."""
    name = row['image_name']; stem = Path(name).stem
    if Path(name).name != name or '/' in name or '\\' in name:raise ValueError('Unsafe image name')
    path = Path(dataset)/'images'/name
    if digest(path) != row['source_sha256']:raise ValueError('Source image hash mismatch')
    receipt_path = Path(uniface)/'receipts'/f'{stem}.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt['source_sha256'] != row['source_sha256'] or receipt['row']['image_name'] != name:
        raise ValueError('Receipt image identity/hash mismatch')
    if metric['status'] != 'success' or receipt['row']['status'] != 'success':
        raise ValueError('UniFace prediction not successful')
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None or image.shape != (256,256,3) or image.dtype != np.uint8:
        raise ValueError('Expected original 256x256 uint8 BGR image')
    masks = {}; lineage = {'image_path':str(path.resolve()),'receipt_sha256':digest(receipt_path)}
    for region in ('skin','hair'):
        relative = f'masks/{region}/{stem}_{region}_mask.png'
        mask_path = Path(uniface)/relative
        fingerprint = digest(mask_path)
        if fingerprint != receipt['artifacts'][relative]:raise ValueError(f'{region} raw-mask hash mismatch')
        mask = load_mask(mask_path, image.shape[:2]); count = int(np.count_nonzero(mask))
        if count != int(metric[region+'_pixels']) or count != int(receipt['row'][region+'_pixels']):
            raise ValueError(f'{region} pixel-count mismatch')
        masks[region] = mask
        lineage.update({region+'_mask_path':str(mask_path.resolve()),region+'_mask_sha256':fingerprint,
                        region+'_pixels':count})
    if np.any((masks['skin']>0)&(masks['hair']>0)):raise ValueError('Raw skin/hair masks overlap')
    return image, masks['skin'], masks['hair'], lineage


def descriptor_checks(matrix):
    if matrix.ndim != 2 or matrix.shape[1] != 144 or not np.isfinite(matrix).all():
        raise ValueError('Invalid finite B144 matrix')
    hist_error = 0.
    for start,stop in ((0,48),(60,70),(72,120),(132,142)):
        hist = matrix[:,start:stop]
        if np.any(hist<0):raise ValueError('Negative raw histogram')
        error = float(np.max(np.abs(hist.sum(axis=1)-1)))
        if error>1e-12:raise ValueError('Raw histogram L1 sum differs from 1')
        hist_error = max(hist_error,error)
    circular = matrix[:,[70,71,142,143]]
    if np.any(circular<0) or np.any(circular>1):raise ValueError('Circular values outside [0,1]')
    return {'max_histogram_l1_error':hist_error,'circular_min':float(circular.min()),
            'circular_max':float(circular.max()),'finite':True}


def run(output=DEFAULT_OUTPUT, report=Path('C:/Users/USER/Downloads/csdldpt.pdf'),
        dataset=DATASET, uniface=UNIFACE, metadata=A_METADATA):
    started = time.perf_counter()
    dataset,uniface,metadata,report = (Path(p).resolve() for p in (dataset,uniface,metadata,report))
    output = new_output(output,(dataset,uniface,metadata.parent,
                                ROOT/'outputs/B_color/color_features_100',ROOT/'outputs/B_color/color_evaluation_10'))
    if digest(report) != SCHEMA['report_sha256']:raise ValueError('Official report hash mismatch')
    a_rows = read_csv(metadata); manifest = read_csv(uniface/'manifest.csv')
    a_index = unique_index(a_rows,'image_name'); full = unique_index(manifest,'image_name')
    metrics = unique_index(read_csv(uniface/'metrics.csv'),'image_name')
    if len(a_rows)!=1438 or set(a_index)!=set(full) or set(full)!=set(metrics):
        raise ValueError('Expected exactly 1438 matching A metadata/UniFace/metrics identities')
    if {p.name for p in (dataset/'images').glob('*.png')} != set(a_index):
        raise ValueError('Dataset image identities differ from metadata')
    ids = [r.get('image_id') or Path(r['image_name']).stem for r in a_rows]
    if len(set(ids))!=1438:raise ValueError('Duplicate image IDs')
    segmentation = json.loads((uniface/'summary.json').read_text(encoding='utf-8'))
    model = segmentation['model']
    if digest(Path(model['model_path'])) != model['model_sha256']:
        raise ValueError('Existing segmentation model hash mismatch; no downloads permitted')
    model_hash_before = digest(Path(model['model_path']))
    metadata_hashes = {str(p):digest(p) for p in (metadata,uniface/'manifest.csv',uniface/'metrics.csv',uniface/'summary.json',report)}
    before = protect_state(dataset,output)
    output.mkdir(parents=True,exist_ok=True)
    write_json(output/'protected_inputs_before.json',before)
    write_json(output/'schema.json',SCHEMA)
    write_json(output/'model_info.json',dict(model,new_inferences=0,
        source_summary=str(uniface/'summary.json'),source_summary_sha256=digest(uniface/'summary.json')))
    save_csv(output/'feature_layout.csv',[{'index':i,'name':name} for i,name in enumerate(feature_names())],['index','name'])
    vectors = []; rows = []; extraction_started = time.perf_counter()
    for a_row_index, a_row in enumerate(a_rows):
        name = a_row['image_name']; original = full[name]; metric = metrics[name]
        base = dict(a_row_index=a_row_index,image_id=ids[a_row_index],image_name=name,
                    dataset_source=original['dataset_source'],source_sha256=original['source_sha256'],
                    status='invalid_input',reason='',feature_row_index='',input_verified=False,
                    uniface_warning=metric.get('warning',''),warning='')
        image_start = time.perf_counter()
        try:
            if original['dataset_source'] != ('CFD' if name.startswith('cfd_final_') else 'HF' if name.startswith('hf_merged_') else ''):
                raise ValueError('Unexpected dataset source/prefix')
            image,skin,hair,lineage = verified_input(dataset,uniface,original,metric)
            base.update(lineage,input_verified=True)
        except Exception as error:
            base.update(reason=f'{type(error).__name__}: {error}')
        else:
            try:
                result = extract_color(image,skin,hair,min_pixels=100)
                base.update(skin_status=result.skin['status'],hair_status=result.hair['status'],
                    skin_low_saturation_fraction=result.skin.get('low_saturation_fraction',''),
                    hair_low_saturation_fraction=result.hair.get('low_saturation_fraction',''))
                warning = [w for w in metric.get('warning','').split(';') if w and not w.startswith(('skin_clean:','hair_clean:'))]
                warning += [region+':'+w for region,info in (('skin',result.skin),('hair',result.hair)) for w in info['warnings']]
                base['warning'] = ';'.join(warning)
                if result.vector is None:
                    reasons = [f'{region}:{info["status"]}({info["pixels"]}<100)' for region,info in (('skin',result.skin),('hair',result.hair)) if info['pixels']<100]
                    base.update(status='missing_region',reason=';'.join(reasons))
                else:
                    base.update(status='valid',feature_row_index=len(vectors))
                    vectors.append(result.vector)
            except Exception as error:
                base.update(status='extraction_failed',reason=f'{type(error).__name__}: {error}')
        base['processing_time_ms'] = (time.perf_counter()-image_start)*1000
        rows.append(base)
        if (a_row_index+1)%100==0 or a_row_index==1437:
            print(f'[{a_row_index+1}/1438] valid={len(vectors)}',flush=True)
    extraction_seconds = time.perf_counter()-extraction_started
    valid = [r for r in rows if r['status']=='valid']; missing = [r for r in rows if r['status']!='valid']
    save_csv(output/'manifest.csv',rows,FIELDS)
    save_csv(output/'feature_rows.csv',valid,FIELDS)
    save_csv(output/'missing_features.csv',missing,FIELDS)
    save_csv(output/'review_candidates.csv',[r for r in rows if r['warning'] or r['status']!='valid'],FIELDS)
    if len(vectors)<2:raise ValueError('At least two valid vectors required; see manifest')
    raw = np.asarray(vectors,dtype=np.float64).reshape(-1,144)
    checks = descriptor_checks(raw)
    stats = fit_standardizer(raw,profile='all144'); z = transform(raw,stats)
    if z.shape != raw.shape or not np.isfinite(z).all():raise ValueError('Invalid Z-score matrix')
    np.save(output/'features_B_raw.npy',raw,allow_pickle=False)
    np.save(output/'features_B_normalized.npy',z,allow_pickle=False)
    fit_fields = ['feature_row_index','a_row_index','image_id','image_name','source_sha256','skin_pixels','hair_pixels']
    save_csv(output/'fit_manifest.csv',valid,fit_fields)
    np.savez(output/'normalization_stats.npz',mean=stats['mean'],std=stats['std'],
        raw_std=raw.std(axis=0,ddof=0),constant_dimensions=stats['constant_dimensions'],
        fit_count=len(valid),profile='all144',schema_id=SCHEMA['id'],fit_manifest_sha256=digest(output/'fit_manifest.csv'))
    distribution = [{'index':i,'name':name,'raw_min':float(raw[:,i].min()),'raw_max':float(raw[:,i].max()),
                     'raw_mean':float(stats['mean'][i]),'raw_std':float(raw[:,i].std()),'divisor':float(stats['std'][i]),
                     'z_mean':float(z[:,i].mean()),'z_std':float(z[:,i].std()),'max_abs_z':float(np.max(np.abs(z[:,i])))}
                    for i,name in enumerate(feature_names())]
    save_csv(output/'feature_distribution.csv',distribution,list(distribution[0]))
    outliers = [dict(image_id=r['image_id'],image_name=r['image_name'],max_abs_z=float(np.max(np.abs(z[i]))),
                     dimensions=';'.join(feature_names()[j] for j in np.flatnonzero(np.abs(z[i])>5)))
                for i,r in enumerate(valid) if np.max(np.abs(z[i]))>5]
    save_csv(output/'feature_outliers.csv',outliers,['image_id','image_name','max_abs_z','dimensions'])
    after = protect_state(dataset,output)
    if before != after or any(digest(Path(p))!=h for p,h in metadata_hashes.items()) or digest(Path(model['model_path']))!=model_hash_before:
        raise RuntimeError('Protected inputs changed during extraction')
    source = output/'source_snapshot'; source.mkdir()
    for name in ('full_color.py','color_features.py','audit_color_inputs.py','run_color_experiment.py'):
        (source/(name+'.txt')).write_bytes((ROOT/'features/B_color/src'/name).read_bytes())
    summary = dict(schema_id=SCHEMA['id'],approval_date=SCHEMA['approval_date'],images=1438,
        valid_vectors=len(valid),missing_features=len(missing),statuses=dict(Counter(r['status'] for r in rows)),
        shape=list(raw.shape),normalized_shape=list(z.shape),dtype=str(raw.dtype),mask_variant='raw',
        normalization_profile='all144',fit_count=len(valid),constant_dimensions=stats['constant_dimensions'].tolist(),
        normalization_max_abs_mean=float(np.max(np.abs(z[:,raw.std(axis=0)>=1e-8].mean(axis=0)))),
        normalization_max_std_error=float(np.max(np.abs(z[:,raw.std(axis=0)>=1e-8].std(axis=0)-1))),
        warnings_all_manifest=sum(bool(r['warning']) for r in rows),warnings_valid_vectors=sum(bool(r['warning']) for r in valid),
        z_outlier_images=len(outliers),by_source={s:{'images':sum(r['dataset_source']==s for r in rows),
            'valid_vectors':sum(r['dataset_source']==s for r in valid),'missing_features':sum(r['dataset_source']==s for r in missing),
            'warnings':sum(r['dataset_source']==s and bool(r['warning']) for r in rows)} for s in ('CFD','HF')},
        verified_input_images=sum(r['input_verified'] for r in rows),raw_mask_files_verified=2*sum(r['input_verified'] for r in rows),
        metadata_order='A metadata.csv, a_row_index preserved; compact feature rows exclude missing data',
        metadata_order_matches_uniface=[r['image_name'] for r in a_rows]==[r['image_name'] for r in manifest],
        input_metadata_sha256=metadata_hashes,model=model,new_inferences=0,
        protected_files_unchanged=len(before),extraction_seconds=extraction_seconds,
        wall_time_seconds=time.perf_counter()-started,environment={'python':platform.python_version(),'numpy':np.__version__,'opencv':cv2.__version__},
        report_sha256=SCHEMA['report_sha256'],**checks)
    write_json(output/'summary.json',summary)
    core = ['schema.json','features_B_raw.npy','features_B_normalized.npy','normalization_stats.npz',
            'manifest.csv','feature_rows.csv','fit_manifest.csv','model_info.json','summary.json']
    write_json(output/'gallery_integrity.json',{name:digest(output/name) for name in core})
    return summary


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    cli.add_argument('--report',type=Path,default=Path('C:/Users/USER/Downloads/csdldpt.pdf'))
    args = cli.parse_args()
    print(json.dumps(run(args.output,args.report),indent=2))


if __name__ == '__main__':main()
