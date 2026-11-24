"""Approved B-only Top-5 and new-image queries using saved full-gallery statistics."""
import argparse
from collections import Counter
import json
from pathlib import Path

import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import ROOT, DATASET, read_csv, digest, load_mask
from features.B_color.src.color_features import extract_color, transform
from features.B_color.src.full_color import SCHEMA, DEFAULT_OUTPUT, descriptor_checks, new_output
from features.B_color.src.run_color_experiment import save_csv, save_png, write_json
from features.B_color.src.evaluate_color_retrieval import select_queries, LAB_INDICES, check_conventions


def load_gallery(gallery):
    gallery = Path(gallery).resolve()
    integrity = json.loads((gallery/'gallery_integrity.json').read_text(encoding='utf-8'))
    for name,expected in integrity.items():
        path = (gallery/name).resolve()
        if gallery not in path.parents or digest(path)!=expected:raise ValueError('Gallery integrity mismatch: '+name)
    schema = json.loads((gallery/'schema.json').read_text(encoding='utf-8'))
    if schema != SCHEMA:raise ValueError('Gallery schema differs from approved B144 v1')
    rows = read_csv(gallery/'feature_rows.csv')
    raw = np.load(gallery/'features_B_raw.npy',allow_pickle=False)
    z = np.load(gallery/'features_B_normalized.npy',allow_pickle=False)
    if raw.shape!=(len(rows),144) or z.shape!=raw.shape or not np.isfinite(z).all():raise ValueError('Invalid gallery vectors')
    descriptor_checks(raw)
    with np.load(gallery/'normalization_stats.npz',allow_pickle=False) as file:
        stats = {k:file[k].copy() for k in file.files}
    if str(stats['schema_id'])!=SCHEMA['id'] or str(stats['profile'])!='all144' or int(stats['fit_count'])!=len(rows):
        raise ValueError('Gallery normalization provenance mismatch')
    if str(stats['fit_manifest_sha256'])!=digest(gallery/'fit_manifest.csv'):raise ValueError('Fit manifest hash mismatch')
    if any(stats[key].shape!=(144,) or not np.isfinite(stats[key]).all() for key in ('mean','std','raw_std')):
        raise ValueError('Invalid normalization parameter dimensions')
    if np.any(stats['std']<=0):raise ValueError('Invalid normalization divisor')
    if len({r['image_id'] for r in rows})!=len(rows) or len({r['image_name'] for r in rows})!=len(rows):
        raise ValueError('Duplicate gallery identities')
    np.testing.assert_array_equal(z,transform(raw,stats))
    return rows,raw,z,stats


def rank(query_z, gallery_z, rows, image_id=None):
    query_z = np.asarray(query_z,dtype=np.float64)
    gallery_z = np.asarray(gallery_z,dtype=np.float64)
    if query_z.shape!=(144,) or gallery_z.shape!=(len(rows),144) or not np.isfinite(query_z).all() or not np.isfinite(gallery_z).all():
        raise ValueError('Expected finite B144 query/gallery vectors')
    if len({r['image_id'] for r in rows})!=len(rows) or len({r['image_name'] for r in rows})!=len(rows):
        raise ValueError('Duplicate gallery identities')
    distances = np.linalg.norm(gallery_z-query_z,axis=1)
    for i,row in enumerate(rows):
        if image_id is not None and row['image_id']==image_id:distances[i]=np.inf
    ordered = np.lexsort((np.array([r['image_name'] for r in rows]),distances))
    return [{'rank':n,'image_id':rows[i]['image_id'],'image_name':rows[i]['image_name'],
             'dataset_source':rows[i]['dataset_source'],'distance':float(distances[i])}
            for n,i in enumerate([i for i in ordered if np.isfinite(distances[i])][:5],1)]


def preview(query_image, query_name, results, rows, title):
    index = {r['image_id']:r for r in rows}
    canvas = np.full((338,1536,3),255,np.uint8)
    for i,name in enumerate([query_name]+[r['image_name'] for r in results]):
        image = query_image if i==0 else cv2.imread(index[results[i-1]['image_id']]['image_path'])
        if image is None or image.shape!=(256,256,3):raise ValueError('Invalid preview image')
        canvas[35:291,i*256:(i+1)*256] = image
        label = 'QUERY' if i==0 else f'TOP {i} D={results[i-1]["distance"]:.4f}'
        cv2.putText(canvas,label,(i*256+5,313),0,.5,(0,0,0),1,cv2.LINE_AA)
        cv2.putText(canvas,name,(i*256+5,331),0,.4,(0,0,0),1,cv2.LINE_AA)
    cv2.putText(canvas,title,(8,24),0,.55,(0,0,0),1,cv2.LINE_AA)
    return canvas


def evaluate(gallery=DEFAULT_OUTPUT):
    gallery = Path(gallery).resolve()
    rows,raw,z,stats = load_gallery(gallery)
    output = gallery/'retrieval'
    if output.exists() and any(output.iterdir()):raise FileExistsError('Retrieval output already exists')
    output.mkdir(exist_ok=True)
    selected = select_queries(raw,rows)  # Existing deterministic 5 CFD + 5 HF color coverage.
    query_rows = []; results = []; panels = []; overview = []; convention_rows = []
    for index in selected:
        row = rows[index]; q = row['image_name']
        image = cv2.imread(row['image_path'])
        if digest(Path(row['image_path']))!=row['source_sha256']:raise ValueError('Query source image changed')
        query_z = transform(raw[index],stats)
        np.testing.assert_array_equal(query_z,z[index])
        ranking = rank(query_z,z,rows,row['image_id'])
        results += [dict(query_id=row['image_id'],query_name=q,**r) for r in ranking]
        panel = preview(image,q,ranking,rows,f'B144 raw v1.0.0 | all144 Z-score | Euclidean | gallery={len(rows)}')
        panels.append(panel)
        save_png(output/'queries'/f'{Path(q).stem}_top5.png',panel)
        tile = cv2.copyMakeBorder(image,30,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
        cv2.putText(tile,q,(4,20),0,.45,(255,255,255),1,cv2.LINE_AA); overview.append(tile)
        colors = raw[index,LAB_INDICES]
        query_rows.append(dict(image_id=row['image_id'],image_name=q,dataset_source=row['dataset_source'],
            a_row_index=row['a_row_index'],feature_row_index=index,warning=row['warning'],
            **{key:float(v) for key,v in zip(('skin_L','skin_a','skin_b','hair_L','hair_a','hair_b'),colors)},
            selection='5 per source; deterministic farthest coverage in raw mean Lab; selection scaling never used for ranking'))
        for region,offset in (('skin',0),('hair',72)):
            mask_path = Path(row[region+'_mask_path'])
            if digest(mask_path)!=row[region+'_mask_sha256']:raise ValueError('Query raw mask changed')
            check = check_conventions(image,load_mask(mask_path,(256,256)),raw[index,offset:offset+72])
            convention_rows.append(dict(image_name=q,region=region,**check))
    for i in range(0,10,5):save_png(output/'contact_sheet'/f'page_{i//5+1:02}.png',np.vstack(panels[i:i+5]))
    save_png(output/'query_overview.png',np.vstack([np.hstack(overview[i:i+5]) for i in (0,5)]))
    save_csv(output/'query_manifest.csv',query_rows,list(query_rows[0]))
    save_csv(output/'top5.csv',results,list(results[0]))
    save_csv(output/'convention_recompute.csv',convention_rows,list(convention_rows[0]))
    summary = dict(queries=len(selected),query_sources=dict(Counter(r['dataset_source'] for r in query_rows)),
        gallery_vectors=len(rows),result_rows=len(results),self_matches=sum(r['query_id']==r['image_id'] for r in results),
        max_query_z_error=0.,max_circular_std_error=max(r['circular_std_error'] for r in convention_rows),
        max_kurtosis_error=max(r[c+'_kurtosis_error'] for r in convention_rows for c in ('L','a','b')),
        contact_pages=2,selection='mean-Lab color coverage; predicted masks, not ground truth',
        quality_claim='Visual review only; no accuracy/relevance labels and no formula optimization')
    write_json(output/'summary.json',summary)
    load_gallery(gallery)  # Prove that query evaluation did not refit/modify core gallery files.
    return summary


def query_image(gallery, image_path, skin_path, hair_path, output, image_id=None):
    gallery = Path(gallery).resolve()
    output = new_output(output,(DATASET,ROOT/'outputs/B_color/uniface_full',
                                ROOT/'outputs/B_color/color_features_100',ROOT/'outputs/B_color/color_evaluation_10'))
    if output==gallery or output in gallery.parents:raise ValueError('Query output must not replace gallery')
    rows,_,z,stats = load_gallery(gallery)
    image_path,skin_path,hair_path = [Path(p).resolve() for p in (image_path,skin_path,hair_path)]
    inputs = {str(p):digest(p) for p in (image_path,skin_path,hair_path)}
    image = cv2.imread(str(image_path),cv2.IMREAD_UNCHANGED)
    if image is None or image.shape!=(256,256,3) or image.dtype!=np.uint8:
        raise ValueError('New query must be an aligned 256x256 uint8 portrait')
    skin = load_mask(skin_path,(256,256)); hair = load_mask(hair_path,(256,256))
    result = extract_color(image,skin,hair,min_pixels=100)
    status = dict(schema_id=SCHEMA['id'],image_name=image_path.name,image_id=image_id,
        gallery=str(gallery),normalization_stats_sha256=digest(gallery/'normalization_stats.npz'),
        gallery_feature_rows_sha256=digest(gallery/'feature_rows.csv'),
        input_sha256=inputs,skin=result.skin,hair=result.hair,
        mask_lineage='Caller-supplied binary raw masks must correspond to UniFace classes 1 and 17; semantic quality not confirmed',
        status='valid' if result.vector is not None else 'missing_region',fit_reused=True,query_refit=False)
    if image_id is None:
        matches = [r['image_id'] for r in rows if r['source_sha256']==inputs[str(image_path)]]
        if len(matches)>1:raise ValueError('Ambiguous image identity; supply --image-id')
        image_id = matches[0] if matches else None
        status['image_id'] = image_id
    output.mkdir(parents=True,exist_ok=True)
    if result.vector is not None:
        qz = transform(result.vector,stats)
        ranking = rank(qz,z,rows,image_id)
        np.save(output/'query_B_raw.npy',result.vector,allow_pickle=False)
        np.save(output/'query_B_normalized.npy',qz,allow_pickle=False)
        save_csv(output/'top5.csv',ranking,['rank','image_id','image_name','dataset_source','distance'])
        save_png(output/'top5.png',preview(image,image_path.name,ranking,rows,'New query | B144 raw v1.0.0 | saved gallery Z-score'))
    write_json(output/'query_status.json',status)
    if any(digest(Path(p))!=h for p,h in inputs.items()):raise RuntimeError('Query inputs changed')
    load_gallery(gallery)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gallery',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--image',type=Path)
    parser.add_argument('--skin-mask',type=Path)
    parser.add_argument('--hair-mask',type=Path)
    parser.add_argument('--image-id')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if args.image:
        if not all((args.skin_mask,args.hair_mask,args.output)):parser.error('New image requires --skin-mask, --hair-mask and --output')
        result = query_image(args.gallery,args.image,args.skin_mask,args.hair_mask,args.output,args.image_id)
    else:
        if any((args.skin_mask,args.hair_mask,args.image_id,args.output)):parser.error('Query options require --image')
        result = evaluate(args.gallery)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':main()
