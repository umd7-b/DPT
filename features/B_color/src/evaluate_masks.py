"""Score predictions ONLY against independently drawn, human-confirmed labels."""
import argparse
import json
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import numpy as np

from features.B_color.src.mask_labels import (Annotation, DATASET, LABELS, REGIONS, ROOT, WORK,
                         binary_mask, digest, image_names, overlay, safe_destination, tile, write_csv, write_image)


def metrics(prediction, truth):
    if prediction.shape != truth.shape:
        raise ValueError('Prediction/GT dimensions differ')
    p, g = prediction > 0, truth > 0
    tp, fp, fn = int(np.sum(p & g)), int(np.sum(p & ~g)), int(np.sum(~p & g))
    # Undefined ratios are blank, not invented perfect scores for empty masks.
    ratio = lambda a, b: a / b if b else ''
    return {'tp':tp, 'fp':fp, 'fn':fn, 'iou':ratio(tp,tp+fp+fn),
            'dice':ratio(2*tp,2*tp+fp+fn), 'precision':ratio(tp,tp+fp), 'recall':ratio(tp,tp+fn)}


def evaluate(names, dataset, labels, skin_dir, hair_dir, output):
    safe_destination(output,dataset,labels,skin_dir,hair_dir)
    output.mkdir(parents=True,exist_ok=True)
    rows = []
    for name in names:
        image_path = dataset / 'images' / name
        annotation = None
        invalid = ''
        if (labels / image_path.stem / 'current.json').exists():
            try: annotation = Annotation(image_path,labels)
            except (ValueError,OSError,KeyError,TypeError) as error: invalid = str(error)
        image = cv2.imread(str(image_path))
        for region in REGIONS:
            row = {'filename':name, 'region':region, 'status':'missing_manual_label',
                   'prediction_kind':'unverified_dataset_template' if region == 'skin' else 'algorithm_prediction'}
            pred_path = (skin_dir / f'{image_path.stem}_skin.png' if region == 'skin'
                         else hair_dir / f'{image_path.stem}_hair_mask.png')
            row['prediction_path'] = str(pred_path)
            if invalid:
                row.update(status='invalid_manual_label',reason=invalid)
            elif annotation is not None:
                if not annotation.valid_region(region):
                    row['status'] = 'unconfirmed_manual_label'
                elif not pred_path.exists():
                    row['status'] = 'missing_prediction'
                else:
                    try:
                        prediction = binary_mask(pred_path,annotation.image.shape[:2])
                        truth = annotation.masks[region]
                        row.update(status='evaluated',reviewer=annotation.review[region]['reviewer'],
                                   source_sha256=annotation.source_hash,prediction_sha256=digest(pred_path),
                                   gt_revision=json.loads((annotation.directory/'current.json').read_text())['revision'],
                                   gt_pixels=int(np.count_nonzero(truth)),pred_pixels=int(np.count_nonzero(prediction)),
                                   **metrics(prediction,truth))
                        error_map = np.zeros_like(image)
                        error_map[(prediction>0)&(truth>0)] = (0,200,0)
                        error_map[(prediction>0)&(truth==0)] = (0,0,255)
                        error_map[(prediction==0)&(truth>0)] = (255,0,0)
                        comparison = np.hstack([tile(image,name),
                            tile(overlay(image,prediction,(255,80,20)),'Prediction'),
                            tile(overlay(image,truth,(0,220,0)),'Human-confirmed GT'),
                            tile(error_map,'TP green FP red FN blue')])
                        write_image(output / 'comparisons' / f'{image_path.stem}_{region}.png',comparison)
                    except (ValueError,OSError,cv2.error) as error:
                        row.update(status='invalid_prediction',reason=str(error))
            if row['status'] != 'evaluated' and image is not None:
                # Explicitly show missing/unconfirmed GT; never render a blank mask as GT.
                pred_panel = tile(image.copy(),'Prediction unavailable')
                if pred_path.exists():
                    try: pred_panel = tile(overlay(image,binary_mask(pred_path,image.shape[:2]),(255,80,20)),'Prediction (unscored)')
                    except ValueError: pass
                unavailable = tile(np.full_like(image,35),'NO VALID HUMAN GT')
                write_image(output / 'comparisons' / f'{image_path.stem}_{region}.png',
                            np.hstack([tile(image,name),pred_panel,unavailable]))
            rows.append(row)
    fields = ['filename','region','status','reason','prediction_kind','prediction_path','reviewer',
              'source_sha256','prediction_sha256','gt_revision',
              'gt_pixels','pred_pixels','tp','fp','fn','iou','dice','precision','recall']
    write_csv(output / 'metrics.csv',rows,fields)
    summary = {}
    for region in REGIONS:
        valid = [r for r in rows if r['region']==region and r['status']=='evaluated']
        summary[region] = {'evaluated':len(valid), 'requested':len(names),
                           'coverage':len(valid)/len(names) if names else 0}
        for metric in ('iou','dice','precision','recall'):
            values = [r[metric] for r in valid if r[metric] != '']
            summary[region]['macro_'+metric] = float(np.mean(values)) if values else None
            summary[region][metric+'_defined_count'] = len(values)
    (output / 'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--manifest',type=Path,default=WORK / 'panel40.csv')
    parser.add_argument('--image',nargs='+')
    parser.add_argument('--labels',type=Path,default=LABELS)
    parser.add_argument('--skin-pred-dir',type=Path)
    parser.add_argument('--hair-pred-dir',type=Path,default=WORK / 'predictions/hair')
    parser.add_argument('--output',type=Path,default=WORK / 'evaluation')
    args = parser.parse_args()
    names = args.image or image_names(args.manifest)
    if any(Path(n).name != n or '/' in n or '\\' in n for n in names): parser.error('Image basenames required')
    evaluate(names,args.dataset,args.labels,args.skin_pred_dir or args.dataset/'skin_masks',args.hair_pred_dir,args.output)


if __name__ == '__main__':
    main()
