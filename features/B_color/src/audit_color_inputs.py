"""Read-only mask/order preflight for B. Does not define/extract color features."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
DATASET=Path(r'D:\TuNam4\dataset_HF_CFD_final')
UNIFACE=ROOT/'outputs/B_color/uniface_full'
SAMPLE=ROOT/'outputs/B_color/uniface_batch_100/manifest.csv'
A_METADATA=ROOT/'outputs/A_geometry/features/metadata.csv'


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique_index(rows,key):
    names=[r[key] for r in rows]
    if len(names)!=len(set(names)):raise ValueError(f'Duplicate {key}')
    if any(Path(n).name!=n or '/' in n or '\\' in n for n in names):raise ValueError('Unsafe image name')
    return {r[key]:r for r in rows}


def align_sample(a_rows,full_rows,sample_rows):
    a=unique_index(a_rows,'image_name')
    full=unique_index(full_rows,'image_name')
    sample=unique_index(sample_rows,'image_name')
    if set(a)!=set(full):raise ValueError('A/full image sets differ')
    if not set(sample).issubset(a):raise ValueError('Sample contains images absent from A')
    return [(i,r['image_name']) for i,r in enumerate(a_rows) if r['image_name'] in sample]


def region_status(pixels,minimum=100):
    if minimum<1 or pixels<0:raise ValueError('Invalid pixel threshold/count')
    if pixels==0:return 'missing_empty'
    if pixels<minimum:return 'insufficient_pixels'
    return 'available_not_quality_approved'


def load_mask(path,shape):
    m=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if m is None or m.dtype!=np.uint8 or m.shape!=shape or not set(np.unique(m)).issubset({0,255}):
        raise ValueError(f'Invalid binary mask: {path}')
    return m


def audit(dataset=DATASET,uniface=UNIFACE,sample_path=SAMPLE,a_path=A_METADATA,
          output=ROOT/'outputs/B_color/feature_input_audit',minimum=100):
    dataset,uniface,output=map(Path,(dataset,uniface,output))
    if minimum<1:raise ValueError('minimum must be >=1')
    for protected in (dataset,uniface,Path(sample_path).parent,Path(a_path).parent):
        dest,src=output.resolve(),protected.resolve()
        if dest==src or src in dest.parents or dest in src.parents:
            raise ValueError('Audit output overlaps protected inputs')
    if output.exists() and any(output.iterdir()):raise FileExistsError('Audit output must be new/empty')
    a_rows=read_csv(a_path);full_rows=read_csv(uniface/'manifest.csv');sample_rows=read_csv(sample_path)
    order=align_sample(a_rows,full_rows,sample_rows)
    full=unique_index(full_rows,'image_name'); sample=unique_index(sample_rows,'image_name')
    metrics=unique_index(read_csv(uniface/'metrics.csv'),'image_name')
    if set(metrics)!=set(full):raise ValueError('Full metrics/manifest image sets differ')
    selected=[];results=[];mask_files=0
    source_fingerprints={str(p):digest(p) for p in (Path(a_path),Path(sample_path),uniface/'manifest.csv',uniface/'metrics.csv')}
    for a_index,name in order:
        p=dataset/'images'/name;stem=Path(name).stem
        row={'a_row_index':a_index,'image_name':name,'sample_manifest_index':sample[name]['index'],
             'dataset_source':full[name]['dataset_source'],'source_sha256':full[name]['source_sha256']}
        selected.append(row)
        try:
            source_hash=digest(p)
            if source_hash!=full[name]['source_sha256'] or source_hash!=sample[name]['source_sha256']:
                raise ValueError('Image SHA-256 mismatch')
            if metrics[name]['status']!='success':raise ValueError('UniFace inference not successful')
            image=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
            if image is None or image.shape!=(256,256,3) or image.dtype!=np.uint8:
                raise ValueError('Invalid source image')
            receipt=json.loads((uniface/'receipts'/f'{stem}.json').read_text(encoding='utf-8'))
            if receipt['source_sha256']!=source_hash:raise ValueError('Receipt/image mismatch')
            masks={}
            for r in ('skin','hair','skin_clean','hair_clean'):
                path=uniface/'masks'/r/f'{stem}_{r}_mask.png'
                if digest(path)!=receipt['artifacts'][path.relative_to(uniface).as_posix()]:raise ValueError('Mask receipt hash mismatch')
                masks[r]=load_mask(path,image.shape[:2]);mask_files+=1
                if np.count_nonzero(masks[r])!=int(metrics[name][r+'_pixels']):raise ValueError('Mask pixel count differs from metrics')
            for r in ('skin','hair'):
                if not np.array_equal(masks[r+'_clean'],cv2.erode(masks[r],np.ones((3,3),np.uint8),iterations=1)):
                    raise ValueError('Stored erosion mismatch')
            for variant in ('raw','clean'):
                skin=masks['skin' if variant=='raw' else 'skin_clean']
                hair=masks['hair' if variant=='raw' else 'hair_clean']
                skin_n,hair_n=int(np.count_nonzero(skin)),int(np.count_nonzero(hair))
                if np.any((skin>0)&(hair>0)):raise ValueError('Overlapping masks')
                results.append(dict(row,variant=variant,skin_pixels=skin_n,hair_pixels=hair_n,
                    skin_status=region_status(skin_n,minimum),hair_status=region_status(hair_n,minimum),
                    status='input_valid',reason='',uniface_warning=metrics[name]['warning']))
        except (OSError,ValueError,KeyError,TypeError) as e:
            results.append(dict(row,variant='both',status='invalid_input',reason=str(e)))
    # Full-dataset status uses saved counts only. No full-dataset histograms/inference.
    missing=[]
    for i,a_row in enumerate(a_rows):
        r=metrics[a_row['image_name']]
        for variant in ('raw','clean'):
            for region in ('skin','hair'):
                key=region+('_clean' if variant=='clean' else '')+'_pixels'
                if r.get(key,'')=='':continue
                status=region_status(int(r[key]),minimum)
                if status!='available_not_quality_approved':
                    missing.append({'a_row_index':i,'image_name':a_row['image_name'],'variant':variant,
                                    'region':region,'pixels':r[key],'status':status})
    output.mkdir(parents=True)
    def save(name,rows,fields):
        with (output/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    save('sample_in_A_order.csv',selected,list(selected[0]))
    fields=list(selected[0])+['variant','skin_pixels','hair_pixels','skin_status','hair_status','status','reason','uniface_warning']
    save('mask_input_checks.csv',results,fields)
    save('full_missing_region_status.csv',missing,['a_row_index','image_name','variant','region','pixels','status'])
    assert all(digest(p)==h for p,h in source_fingerprints.items())
    summary={'academic_formula_status':'not_evaluated_by_input_audit_see_docs_B_color_feature_spec',
             'a_images':len(a_rows),'full_images':len(full_rows),'sample_images':len(selected),
             'full_order_exactly_matches_A':[r['image_name'] for r in a_rows]==[r['image_name'] for r in full_rows],
             'random_sample_original_order_matches_A':[r['image_name'] for r in sample_rows]==[n for _,n in order],
             'sample_output_order':'A row order; explicit original A row index preserved',
             'mask_files_checked':mask_files,'input_variant_rows':len(results),
             'invalid_inputs':[r for r in results if r['status']!='input_valid'],
             'minimum_region_pixels':minimum,'threshold_status':'operational heuristic, not an academic histogram definition or calibrated quality gate',
             'full_missing_region_rows':len(missing),'protected_manifest_hashes':source_fingerprints,
             'vectors_extracted':0,'new_inferences':0}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=DATASET)
    p.add_argument('--uniface',type=Path,default=UNIFACE)
    p.add_argument('--sample-manifest',type=Path,default=SAMPLE)
    p.add_argument('--a-metadata',type=Path,default=A_METADATA)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/B_color/feature_input_audit')
    p.add_argument('--min-region-pixels',type=int,default=100)
    a=p.parse_args();audit(a.dataset,a.uniface,a.sample_manifest,a.a_metadata,a.output,a.min_region_pixels)


if __name__=='__main__':main()
