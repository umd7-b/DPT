"""Exploratory B-only Euclidean Top-5 within one verified 100-image trial."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

from features.B_color.src.audit_color_inputs import ROOT,DATASET,read_csv
from features.B_color.src.run_color_experiment import save_csv,save_png,write_json


def top5(matrix,names,query):
    matrix=np.asarray(matrix,dtype=np.float64)
    if matrix.ndim!=2 or matrix.shape!=(len(names),144) or not np.isfinite(matrix).all():
        raise ValueError('Invalid finite B144 gallery')
    if len(set(names))!=len(names):raise ValueError('Duplicate gallery image names')
    if query not in names:raise ValueError(f'Query absent or excluded for missing data: {query}')
    q=names.index(query)
    distances=np.linalg.norm(matrix-matrix[q],axis=1)
    distances[q]=np.inf
    indices=np.lexsort((np.asarray(names),distances))
    return [{'rank':rank,'image_name':names[int(i)],'distance':float(distances[i])}
            for rank,i in enumerate([i for i in indices if np.isfinite(distances[i])][:5],1)]


def preview(query,results,title):
    canvas=np.full((338,256*6,3),255,np.uint8)
    for index,name in enumerate([query]+[r['image_name'] for r in results]):
        image=cv2.imread(str(DATASET/'images'/name))
        if image is None:raise ValueError(f'Cannot display {name}')
        canvas[35:291,index*256:(index+1)*256]=image
        label='QUERY' if index==0 else f"TOP {index} D={results[index-1]['distance']:.4f}"
        cv2.putText(canvas,label,(index*256+5,313),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1,cv2.LINE_AA)
        cv2.putText(canvas,name,(index*256+5,331),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,0,0),1,cv2.LINE_AA)
    cv2.putText(canvas,title,(8,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,0),1,cv2.LINE_AA)
    return canvas


def run(trial,queries):
    trial=Path(trial)
    summary=json.loads((trial/'summary.json').read_text())
    output=trial/'retrieval'
    if output.exists() and any(output.iterdir()):raise FileExistsError('Retrieval results already exist; use a new trial')
    output.mkdir()
    results={};panels={q:[] for q in queries}
    for variant,info in summary['variants'].items():
        if not info['finite'] or info['valid_vectors']<6:raise ValueError('Gallery vectors must be checked before retrieval')
        directory=trial/variant
        x=np.load(directory/'features_B_normalized.npy',allow_pickle=False)
        names=[r['image_name'] for r in read_csv(directory/'feature_rows.csv')]
        results[variant]={}
        (output/variant).mkdir()
        for q in queries:
            ranking=top5(x,names,q);results[variant][q]=ranking
            save_csv(output/variant/f'{Path(q).stem}_top5.csv',ranking,['rank','image_name','distance'])
            panel=preview(q,ranking,f'{variant} | {summary["normalization_profile"]} | Euclidean | gallery={len(x)}')
            save_png(output/variant/f'{Path(q).stem}_top5.png',panel)
            panels[q].append(panel)
    variants=list(results);comparison=[]
    for q in queries:
        raw={r['image_name'] for r in results[variants[0]][q]};clean={r['image_name'] for r in results[variants[1]][q]}
        comparison.append({'query':q,'raw_clean_top5_shared':len(raw&clean),
                           'raw_clean_top5_overlap_ratio':len(raw&clean)/5,
                           'interpretation':'ranking agreement only; not retrieval accuracy'})
        save_png(output/f'{Path(q).stem}_variants_comparison.png',np.vstack(panels[q]))
    save_csv(output/'raw_clean_comparison.csv',comparison,list(comparison[0]))
    write_json(output/'results.json',results)
    return comparison


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--trial',type=Path,default=ROOT/'outputs/B_color/color_features_100')
    cli.add_argument('--query',nargs='+',default=['cfd_final_00103.png','cfd_final_00716.png','hf_merged_00285.png'])
    a=cli.parse_args();print(run(a.trial,a.query))


if __name__=='__main__':main()
