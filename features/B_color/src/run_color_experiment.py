"""100-image B144 trials. Raw/clean/nose experiments remain separate."""
import argparse
import csv
import json
from pathlib import Path
import time

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import (ROOT,DATASET,UNIFACE,SAMPLE,A_METADATA,
    read_csv,digest,align_sample,load_mask)
from features.B_color.src.color_features import SCHEMA,feature_names,extract_color,fit_standardizer,transform


def save_csv(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)


def write_json(path,data):path.write_text(json.dumps(data,indent=2),encoding='utf-8')


def save_png(path,image):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not cv2.imwrite(str(path),image):raise OSError(f'Cannot write {path}')


def protected_fingerprints():
    folders=['features/A_geometry','features/C1_lbp','features/C2_hog','retrieval','outputs/A_geometry',
             'outputs/C1_lbp','outputs/C2_hog','outputs/retrieval','annotations','models',
             'outputs/B_color/uniface_full','outputs/B_color/uniface_batch_100']
    return {p.relative_to(ROOT).as_posix():digest(p) for folder in folders
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def build_nose_masks(image,labels):
    labels=np.asarray(labels)
    if labels.shape!=image.shape[:2] or labels.dtype.kind not in 'iu' or np.any((labels<0)|(labels>18)):
        raise ValueError('Invalid class map from UniFace')
    return ((labels==1)|(labels==10)).astype(np.uint8)*255,(labels==17).astype(np.uint8)*255


def run(output,report,profile='all144',include_nose=False,minimum=100):
    # Section 2.3.3 explicitly requires the final Z-score on all 144 dimensions.
    # The legacy moments_only helper is an experimental reading of section 2.5.2,
    # not an accepted profile for this report-pinned trial entry point.
    if profile!='all144':
        raise ValueError('Report section 2.3.3 requires all144; moments_only is experimental and is not accepted by this runner')
    output,report=Path(output).resolve(),Path(report).resolve()
    allowed=(ROOT/'outputs/B_color').resolve()
    if output==allowed or allowed not in output.parents:raise ValueError('Use dedicated outputs/B_color subdirectory')
    if output.exists() and any(output.iterdir()):raise FileExistsError('Experiment output must be new/empty')
    if not report.is_file() or digest(report)!=SCHEMA['report_sha256']:raise ValueError('Academic report differs from verified csdldpt.pdf')
    a_rows=read_csv(A_METADATA);full_rows=read_csv(UNIFACE/'manifest.csv');sample_rows=read_csv(SAMPLE)
    if len(sample_rows)!=100:raise ValueError('This trial is restricted to the original 100-image sample')
    order=align_sample(a_rows,full_rows,sample_rows)
    full={r['image_name']:r for r in full_rows};sample={r['image_name']:r for r in sample_rows}
    masks_metrics={r['image_name']:r for r in read_csv(UNIFACE/'metrics.csv')}
    before=protected_fingerprints()
    output.mkdir(parents=True)
    write_json(output/'protected_inputs_before.json',before)
    save_csv(output/'feature_layout.csv',[{'index':i,'name':n} for i,n in enumerate(feature_names())],['index','name'])
    write_json(output/'schema.json',SCHEMA)
    variants=['A_skin1_hair17_raw','B_skin1_hair17_clean']
    if include_nose:variants.append('C_skin1or10_hair17_raw')
    directories={v:output/v for v in variants}
    for d in directories.values():d.mkdir()
    vectors={v:[] for v in variants};records={v:[] for v in variants};statuses={v:[] for v in variants}
    parser=None;model=None;inference_count=0
    if include_nose:
        from features.B_color.src.batch_uniface import create_parser
        parser,model=create_parser()
    start=time.perf_counter()
    for count,(a_index,name) in enumerate(order,1):
        base={'image_name':name,'a_row_index':a_index,'dataset_source':full[name]['dataset_source'],
              'sample_manifest_index':sample[name]['index'],'source_sha256':full[name]['source_sha256']}
        try:
            path=DATASET/'images'/name
            if digest(path)!=base['source_sha256'] or digest(path)!=sample[name]['source_sha256']:raise ValueError('Source hash mismatch')
            image=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
            if image is None or image.shape!=(256,256,3):raise ValueError('Invalid original portrait')
            receipt=json.loads((UNIFACE/'receipts'/f'{path.stem}.json').read_text())
            if receipt['source_sha256']!=base['source_sha256']:raise ValueError('Receipt input mismatch')
            masks={}
            for r in ('skin','hair','skin_clean','hair_clean'):
                p=UNIFACE/'masks'/r/f'{path.stem}_{r}_mask.png'
                if digest(p)!=receipt['artifacts'][p.relative_to(UNIFACE).as_posix()]:raise ValueError('Mask hash mismatch')
                masks[r]=load_mask(p,image.shape[:2])
            pairs={variants[0]:(masks['skin'],masks['hair']),variants[1]:(masks['skin_clean'],masks['hair_clean'])}
        except Exception as error:
            for v in variants:statuses[v].append(dict(base,status='invalid_input',reason=str(error)))
            continue
        if include_nose:
            try:
                inference_count+=1
                labels=np.asarray(parser.parse(image))
                skin,hair=build_nose_masks(image,labels)
                if not np.array_equal(hair,masks['hair']) or not np.array_equal((labels==1).astype(np.uint8)*255,masks['skin']):
                    raise ValueError('New inference labels 1/17 differ from saved predictions')
                pairs[variants[2]]=(skin,hair)
                directory=directories[variants[2]]
                save_png(directory/'class_maps'/name,labels.astype(np.uint8))
                save_png(directory/'masks/skin'/f'{path.stem}_skin_mask.png',skin)
                save_png(directory/'masks/hair'/f'{path.stem}_hair_mask.png',hair)
                save_png(directory/'masks/nose10'/f'{path.stem}_nose10_mask.png',(labels==10).astype(np.uint8)*255)
                comparison=np.hstack([image,cv2.bitwise_and(image,image,mask=masks['skin']),
                                     cv2.bitwise_and(image,image,mask=skin),cv2.bitwise_and(image,image,mask=hair)])
                save_png(directory/'previews'/f'{path.stem}.png',comparison)
            except Exception as error:statuses[variants[2]].append(dict(base,status='nose_inference_failed',reason=str(error)))
        for variant,(skin,hair) in pairs.items():
            try:
                result=extract_color(image,skin,hair,minimum)
                row=dict(base,status='valid' if result.vector is not None else 'missing_region',reason='',
                    skin_pixels=result.skin['pixels'],hair_pixels=result.hair['pixels'],
                    skin_status=result.skin['status'],hair_status=result.hair['status'],
                    warnings=';'.join(['skin:'+w for w in result.skin['warnings']]+['hair:'+w for w in result.hair['warnings']]),
                    uniface_warning=masks_metrics[name]['warning'],
                    skin_hue_resultant=result.skin.get('hue_resultant',''),hair_hue_resultant=result.hair.get('hue_resultant',''),
                    skin_low_saturation_fraction=result.skin.get('low_saturation_fraction',''),hair_low_saturation_fraction=result.hair.get('low_saturation_fraction',''))
                if result.vector is not None:
                    row['feature_row_index']=len(vectors[variant]);vectors[variant].append(result.vector)
                    records[variant].append(dict(row))
                statuses[variant].append(row)
            except Exception as error:statuses[variant].append(dict(base,status='extraction_failed',reason=str(error)))
        print(f'[{count}/100] {name}',flush=True)
    summary={'report_path':str(report),'report_sha256':digest(report),'normalization_profile':profile,
             'conventions_status':SCHEMA['conventions_status'],'sample_images':len(order),'minimum_region_pixels':minimum,
             'gallery_scope':'original 100-image trial only; no full dataset features',
             'nose_experiment_new_inferences':inference_count,'nose_model':model,'variants':{}}
    fields=['image_name','a_row_index','dataset_source','sample_manifest_index','source_sha256','feature_row_index',
            'status','reason','skin_pixels','hair_pixels','skin_status','hair_status','warnings','uniface_warning',
            'skin_hue_resultant','hair_hue_resultant','skin_low_saturation_fraction','hair_low_saturation_fraction']
    for variant,directory in directories.items():
        matrix=np.asarray(vectors[variant],dtype=np.float64).reshape(-1,144)
        np.save(directory/'features_B_unscaled.npy',matrix)
        save_csv(directory/'feature_rows.csv',records[variant],fields)
        save_csv(directory/'sample_status.csv',statuses[variant],fields)
        if len(matrix)>=2:
            stats=fit_standardizer(matrix,profile);z=transform(matrix,stats)
            np.save(directory/'features_B_normalized.npy',z)
            np.savez(directory/'normalization_stats.npz',mean=stats['mean'],std=stats['std'],constant_dimensions=stats['constant_dimensions'])
            distribution=[{'index':i,'name':n,'min':float(matrix[:,i].min()),'max':float(matrix[:,i].max()),
                           'mean':float(matrix[:,i].mean()),'std':float(matrix[:,i].std()),'max_abs_z':float(np.abs(z[:,i]).max())}
                           for i,n in enumerate(feature_names())]
            save_csv(directory/'feature_distribution.csv',distribution,list(distribution[0]))
            outliers=[]
            for i,r in enumerate(records[variant]):
                dimensions=np.flatnonzero(np.abs(z[i])>5)
                if len(dimensions):outliers.append({'image_name':r['image_name'],'max_abs_z':float(np.abs(z[i]).max()),
                                                   'dimensions':';'.join(feature_names()[j] for j in dimensions)})
            save_csv(directory/'feature_outliers.csv',outliers,['image_name','max_abs_z','dimensions'])
            summary['variants'][variant]={'valid_vectors':len(matrix),'shape':list(matrix.shape),'finite':bool(np.isfinite(matrix).all() and np.isfinite(z).all()),
                'missing_or_failed':100-len(matrix),'z_outlier_images':len(outliers),'constant_dimensions':stats['constant_dimensions'].tolist(),
                'skin_hs_hist_mean':matrix[:,:48].mean(axis=0).tolist(),'hair_hs_hist_mean':matrix[:,72:120].mean(axis=0).tolist()}
    after=protected_fingerprints()
    changed=[p for p in before if before[p]!=after.get(p)]
    summary.update(protected_files=len(before),changed_protected_files=changed,wall_time_seconds=time.perf_counter()-start)
    write_json(output/'summary.json',summary)
    if changed:raise RuntimeError('Protected input files changed')
    return summary


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--report',type=Path,required=True)
    cli.add_argument('--output',type=Path,default=ROOT/'outputs/B_color/color_features_100')
    cli.add_argument('--normalization',choices=['all144'],default='all144')
    cli.add_argument('--include-nose-experiment',action='store_true')
    cli.add_argument('--min-region-pixels',type=int,default=100)
    a=cli.parse_args();run(a.output,a.report,a.normalization,a.include_nose_experiment,a.min_region_pixels)


if __name__=='__main__':main()
