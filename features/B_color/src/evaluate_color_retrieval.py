"""Read-only evaluation of existing B144 trial vectors; no retraining/inference."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import ROOT, DATASET, read_csv, digest
from features.B_color.src.color_features import SCHEMA, feature_names, transform
from features.B_color.src.search_color import top5, preview
from features.B_color.src.run_color_experiment import protected_fingerprints, save_csv, save_png, write_json

VARIANTS=('A_skin1_hair17_raw','B_skin1_hair17_clean','C_skin1or10_hair17_raw')
LABELS=('Raw','Clean','Skin + Nose')
LAB_INDICES=np.array([48,52,56,120,124,128])
BLOCKS={'skin_HS':(0,48),'skin_Lab':(48,60),'skin_Hue_hist':(60,70),'skin_circular':(70,72),
        'hair_HS':(72,120),'hair_Lab':(120,132),'hair_Hue_hist':(132,142),'hair_circular':(142,144)}


def select_queries(matrix,rows):
    """Five per source by farthest-point sampling of region mean Lab colors.

    Median/IQR here is used ONLY to choose queries, never for retrieval.
    """
    colors=np.asarray(matrix)[:,LAB_INDICES]
    center=np.median(colors,axis=0)
    spread=np.percentile(colors,75,axis=0)-np.percentile(colors,25,axis=0)
    scaled=(colors-center)/np.where(spread<1e-8,1,spread)
    selected=[]
    for source in ('CFD','HF'):
        pool=[i for i,r in enumerate(rows) if r['dataset_source']==source]
        if len(pool)<5:raise ValueError(f'At least five {source} queries required')
        chosen=[min(pool,key=lambda i:(colors[i,0],rows[i]['image_name']))]
        while len(chosen)<5:
            remaining=sorted((i for i in pool if i not in chosen),key=lambda i:rows[i]['image_name'])
            chosen.append(max(remaining,key=lambda i:min(float(np.linalg.norm(scaled[i]-scaled[j])) for j in chosen)))
        selected.extend(chosen)
    return selected


def verify_normalization(x,z,stats):
    x=np.asarray(x,dtype=np.float64);z=np.asarray(z,dtype=np.float64)
    if x.shape!=z.shape or x.ndim!=2 or x.shape[1]!=144 or not np.isfinite(x).all() or not np.isfinite(z).all():
        raise ValueError('Invalid B144 matrices')
    mean=x.mean(axis=0);raw_std=x.std(axis=0,ddof=0)
    near_zero=np.flatnonzero(raw_std<1e-8)
    expected_std=np.where(raw_std<1e-8,1.,raw_std)
    np.testing.assert_allclose(stats['mean'],mean,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(stats['std'],expected_std,rtol=1e-12,atol=1e-12)
    if np.any(stats['std']<=0):raise ValueError('Invalid stored divisor')
    np.testing.assert_array_equal(np.sort(stats['constant_dimensions']),near_zero)
    expected=(x-stats['mean'])/stats['std']
    np.testing.assert_allclose(z,expected,rtol=0,atol=0)
    active=raw_std>=1e-8
    np.testing.assert_allclose(z[:,active].mean(axis=0),0,atol=1e-10)
    np.testing.assert_allclose(z[:,active].std(axis=0),1,atol=1e-10)
    return {'rows':len(x),'dimensions':144,'exact_zero_variance_count':int(np.sum(raw_std==0)),
            'near_zero_variance_count':len(near_zero),'constant_indices':near_zero.tolist(),
            'max_saved_mean_error':float(np.max(np.abs(stats['mean']-mean))),
            'max_saved_std_error':float(np.max(np.abs(stats['std']-expected_std))),
            'max_reconstruction_error':float(np.max(np.abs(z-expected))),
            'active_max_abs_mean':float(np.max(np.abs(z[:,active].mean(axis=0)))),
            'active_max_std_error':float(np.max(np.abs(z[:,active].std(axis=0)-1))),
            'near_zero_max_abs_z':float(np.max(np.abs(z[:,near_zero]))) if len(near_zero) else 0}


def check_conventions(image,mask,stored):
    """Independent moment/circular recomputation, diagnostic only."""
    pixels=image[mask>0].reshape(-1,1,3)
    if len(pixels)==0:raise ValueError('No pixels for convention audit')
    hsv=cv2.cvtColor(pixels,cv2.COLOR_BGR2HSV).reshape(-1,3)
    lab=cv2.cvtColor(pixels.astype(np.float32)/255,cv2.COLOR_BGR2LAB).reshape(-1,3).astype(np.float64)
    angles=hsv[:,0].astype(np.float64)*2*np.pi/180
    resultant=float(np.clip(abs(np.mean(np.exp(1j*angles))),0,1))
    expected_std=float(min(np.sqrt(-2*np.log(max(resultant,1e-12)))/(2*np.pi),1))
    expected_mean=float(np.angle(np.mean(np.exp(1j*angles)))%(2*np.pi)/(2*np.pi)) if resultant>=1e-8 else 0
    if np.isclose(expected_mean,1,atol=1e-12,rtol=0):expected_mean=0
    np.testing.assert_allclose(stored[71],expected_std,atol=1e-12,rtol=1e-12)
    np.testing.assert_allclose(stored[70],expected_mean,atol=1e-12,rtol=1e-12)
    record={'pixels':len(pixels),'hue_resultant':resultant,'stored_circular_std':float(stored[71]),
            'expected_circular_std':expected_std,'circular_std_error':abs(float(stored[71])-expected_std),
            'std_clip_active':bool(np.sqrt(-2*np.log(max(resultant,1e-12)))/(2*np.pi)>1)}
    for channel,name in enumerate(('L','a','b')):
        centered=lab[:,channel]-lab[:,channel].mean();variance=float(np.mean(centered**2))
        pearson=float(np.mean(centered**4)/(variance**2)) if variance>=1e-24 else 0.
        actual=float(stored[48+channel*4+3])
        np.testing.assert_allclose(actual,pearson,rtol=1e-10,atol=1e-10)
        record.update({name+'_stored_kurtosis':actual,name+'_expected_Pearson':pearson,
                       name+'_excess_alternative':pearson-3 if variance>=1e-24 else '',name+'_kurtosis_error':abs(actual-pearson)})
    return record


def run(trial,output,report):
    trial,output,report=map(lambda p:Path(p).resolve(),(trial,output,report))
    allowed=(ROOT/'outputs/B_color').resolve()
    if output==allowed or allowed not in output.parents or trial==output or trial in output.parents or output in trial.parents:
        raise ValueError('Use a separate B_color evaluation folder, outside the original trial')
    if output.exists() and any(output.iterdir()):raise FileExistsError('Evaluation output must be new/empty')
    if digest(report)!=SCHEMA['report_sha256']:raise ValueError('Report fingerprint differs from verified report')
    trial_summary=json.loads((trial/'summary.json').read_text())
    if trial_summary['normalization_profile']!='all144':raise ValueError('Evaluation expects user-confirmed all144')
    before=protected_fingerprints()
    for p in trial.rglob('*'):
        if p.is_file():before[str(p)]=digest(p)
    for name in ('color_features.py','search_color.py','run_color_experiment.py'):
        p=ROOT/'features/B_color/src'/name;before[str(p)]=digest(p)
    for row in read_csv(trial/'artifact_manifest.csv'):
        if digest(trial/row['path'])!=row['sha256']:raise ValueError(f'Trial artifact changed: {row["path"]}')
    output.mkdir(parents=True)
    x,z,rows,stats,status={},{},{},{},{}
    audit={};constant_rows=[]
    for variant in VARIANTS:
        directory=trial/variant
        x[variant]=np.load(directory/'features_B_unscaled.npy',allow_pickle=False)
        z[variant]=np.load(directory/'features_B_normalized.npy',allow_pickle=False)
        with np.load(directory/'normalization_stats.npz',allow_pickle=False) as a:stats[variant]={k:a[k].copy() for k in a.files}
        rows[variant]=read_csv(directory/'feature_rows.csv')
        status[variant]={r['image_name']:r for r in read_csv(directory/'sample_status.csv')}
        if x[variant].shape!=(100,144) or len(rows[variant])!=100:raise ValueError('Only existing 100-image gallery is supported')
        audit[variant]=verify_normalization(x[variant],z[variant],stats[variant])
        for index in audit[variant]['constant_indices']:
            constant_rows.append({'variant':variant,'index':index,'feature':feature_names()[index],
                                  'raw_min':float(x[variant][:,index].min()),'raw_max':float(x[variant][:,index].max()),
                                  'actual_std':float(x[variant][:,index].std()),'stored_divisor':float(stats[variant]['std'][index]),
                                  'normalized_max_abs':float(np.abs(z[variant][:,index]).max())})
    raw_rows=rows[VARIANTS[0]];gallery_names=[r['image_name'] for r in raw_rows]
    if len(set(gallery_names))!=100:raise ValueError('Duplicate gallery rows')
    for variant in VARIANTS:
        if [r['image_name'] for r in rows[variant]]!=gallery_names:raise ValueError('Variant row mismatch')
    selected=select_queries(x[VARIANTS[0]],raw_rows)
    queries=[gallery_names[i] for i in selected]
    selection=[]
    for i in selected:
        r=raw_rows[i];values=x[VARIANTS[0]][i,LAB_INDICES]
        selection.append({'image_name':r['image_name'],'dataset_source':r['dataset_source'],'a_row_index':r['a_row_index'],
                          **{key:float(value) for key,value in zip(('skin_L','skin_a','skin_b','hair_L','hair_a','hair_b'),values)},
                          'method':'5 per source; farthest mean-Lab coverage; selection scaling separate from ranking'})
    save_csv(output/'query_manifest.csv',selection,list(selection[0]))
    tiles=[]
    for q in queries:
        image=cv2.imread(str(DATASET/'images'/q))
        r=raw_rows[gallery_names.index(q)]
        if image is None or digest(DATASET/'images'/q)!=r['source_sha256']:raise ValueError('Original image changed')
        tile=cv2.copyMakeBorder(image,30,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
        cv2.putText(tile,q,(4,20),0,.45,(255,255,255),1,cv2.LINE_AA);tiles.append(tile)
    save_png(output/'query_overview.png',np.vstack([np.hstack(tiles[i:i+5]) for i in range(0,10,5)]))
    rankings={};tables=[];long_rows=[];distance_rows=[];convention_rows=[];query_z_rows=[];panels=[]
    for qi,q in enumerate(queries,1):
        qidx=gallery_names.index(q);rankings[q]={};view=[]
        image=cv2.imread(str(DATASET/'images'/q))
        for variant,label in zip(VARIANTS,LABELS):
            qz=transform(x[variant][qidx],stats[variant])
            np.testing.assert_array_equal(qz,z[variant][qidx])
            query_z_rows.append({'query':q,'variant':variant,'max_saved_vs_query_error':float(np.max(np.abs(qz-z[variant][qidx])))})
            result=top5(z[variant],gallery_names,q);rankings[q][variant]=result
            view.append(preview(q,result,f'{label} | all144 Z-score | Euclidean | gallery=100 | query {qi}/10'))
            (output/'top5_tables').mkdir(exist_ok=True)
            save_csv(output/'top5_tables'/f'{Path(q).stem}_{label.replace(" ","_").replace("+","plus")}.csv',result,['rank','image_name','distance'])
            for found in result:
                ni=gallery_names.index(found['image_name']);delta=z[variant][qidx]-z[variant][ni]
                pieces={name:float(np.sum(delta[a:b]**2)) for name,(a,b) in BLOCKS.items()}
                np.testing.assert_allclose(sum(pieces.values()),found['distance']**2,atol=1e-10,rtol=1e-12)
                skin_delta=float(np.linalg.norm(x[variant][qidx,LAB_INDICES[:3]]-x[variant][ni,LAB_INDICES[:3]]))
                hair_delta=float(np.linalg.norm(x[variant][qidx,LAB_INDICES[3:]]-x[variant][ni,LAB_INDICES[3:]]))
                flags=[]
                if skin_delta>15:flags.append('inspect_skin_mean_Lab_difference_gt15')
                if hair_delta>20:flags.append('inspect_hair_mean_Lab_difference_gt20')
                if float(status[variant][q].get('hair_low_saturation_fraction') or 0)>.5 or float(status[variant][found['image_name']].get('hair_low_saturation_fraction') or 0)>.5:
                    flags.append('low_saturation_hue_caution')
                long_rows.append({'query':q,'variant':label,**found,'skin_mean_Lab_distance':skin_delta,
                                  'hair_mean_Lab_distance':hair_delta,'inspection_flags':';'.join(flags)})
                distance_rows.append({'query':q,'variant':label,**found,**pieces})
            mask_dir=trial/variant/'masks' if variant==VARIANTS[2] else ROOT/'outputs/B_color/uniface_full/masks'
            for region,offset in (('skin',0),('hair',72)):
                kind=region+'_clean' if variant==VARIANTS[1] else region
                path=mask_dir/kind/f'{Path(q).stem}_{kind}_mask.png'
                mask=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
                check=check_conventions(image,mask,x[variant][qidx,offset:offset+72])
                convention_rows.append({'query':q,'variant':label,'region':region,**check})
        for rank in range(5):
            table={'query':q,'rank':rank+1}
            for v,label in zip(VARIANTS,('raw','clean','skin_nose')):
                table[label+'_name']=rankings[q][v][rank]['image_name'];table[label+'_distance']=rankings[q][v][rank]['distance']
            tables.append(table)
        comparison=np.vstack(view);panels.append(comparison)
        save_png(output/'comparisons'/f'{Path(q).stem}_top5.png',comparison)
        save_png(output/'comparisons'/f'{Path(q).stem}_top5.jpg',comparison)
        print(f'[{qi}/10] {q}',flush=True)
    for i in range(0,10,2):save_png(output/'contact_sheet'/f'page_{i//2+1:02d}.png',np.vstack(panels[i:i+2]))
    agreements=[]
    for q in queries:
        sets=[{r['image_name'] for r in rankings[q][v]} for v in VARIANTS]
        agreements.append({'query':q,'raw_clean_shared':len(sets[0]&sets[1]),'raw_nose_shared':len(sets[0]&sets[2]),
                           'clean_nose_shared':len(sets[1]&sets[2]),'interpretation':'ranking agreement, not accuracy'})
    save_csv(output/'top5_comparison.csv',tables,list(tables[0]))
    save_csv(output/'top5_long.csv',long_rows,list(long_rows[0]))
    save_csv(output/'distance_squared_blocks.csv',distance_rows,list(distance_rows[0]))
    save_csv(output/'normalization_summary.csv',[{'variant':v,**a} for v,a in audit.items()],['variant']+list(next(iter(audit.values()))))
    save_csv(output/'constant_dimensions.csv',constant_rows,['variant','index','feature','raw_min','raw_max','actual_std','stored_divisor','normalized_max_abs'])
    save_csv(output/'query_normalization.csv',query_z_rows,list(query_z_rows[0]))
    save_csv(output/'convention_recompute.csv',convention_rows,list(convention_rows[0]))
    save_csv(output/'ranking_agreement.csv',agreements,list(agreements[0]))
    flagged=[r for r in long_rows if 'inspect_' in r['inspection_flags']]
    save_csv(output/'review_candidates.csv',flagged,list(long_rows[0]))
    write_json(output/'rankings.json',rankings)
    after=protected_fingerprints()
    for p in trial.rglob('*'):
        if p.is_file():after[str(p)]=digest(p)
    for name in ('color_features.py','search_color.py','run_color_experiment.py'):
        p=ROOT/'features/B_color/src'/name;after[str(p)]=digest(p)
    if before!=after:raise RuntimeError('Protected existing inputs changed')
    summary={'queries':queries,'query_sources':dict(Counter(r['dataset_source'] for r in selection)),
             'gallery_images':100,'result_rows':len(long_rows),'normalization':audit,
             'normalization_profile':'all144','constant_dimension_policy':'saved divisor 1 below std 1e-8; no dimensions removed',
             'max_query_z_error':max(r['max_saved_vs_query_error'] for r in query_z_rows),
             'max_circular_std_error':max(r['circular_std_error'] for r in convention_rows),
             'max_kurtosis_error':max(r[c+'_kurtosis_error'] for r in convention_rows for c in ('L','a','b')),
             'circular_std_clip_count':sum(r['std_clip_active'] for r in convention_rows),
             'auxiliary_review_pairs':len(flagged),'mean_raw_clean_top5_shared':float(np.mean([r['raw_clean_shared'] for r in agreements])),
             'protected_files_unchanged':len(before),'report_sha256':digest(report),
             'report_conventions_status':'report specifies names/[0,1] but not Pearson/excess or circular-std scaling; exact unique match cannot be asserted',
             'algorithm_changes':False,'new_inferences':0,'new_features_extracted':0}
    write_json(output/'summary.json',summary)
    return summary


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--trial',type=Path,default=ROOT/'outputs/B_color/color_features_100')
    cli.add_argument('--output',type=Path,default=ROOT/'outputs/B_color/color_evaluation_10')
    cli.add_argument('--report',type=Path,default=Path('C:/Users/USER/Downloads/csdldpt.pdf'))
    a=cli.parse_args();print(json.dumps(run(a.trial,a.output,a.report),indent=2))


if __name__=='__main__':main()
