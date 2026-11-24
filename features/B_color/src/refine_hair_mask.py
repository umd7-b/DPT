"""Landmark guided hair segmentation, without extra models.

Run with .venv311/Scripts/python.exe src/refine_hair_mask.py --test.
Area/overlap diagnostics are quality indicators, not segmentation accuracy.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import mediapipe as mp
import numpy as np

ROOT = PROJECT_ROOT
DATASET = Path(r'D:\TuNam4\dataset_HF_CFD_final')
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
TARGETS = ['cfd_final_00001.png', 'cfd_final_00069.png', 'cfd_final_00088.png']
# Fixed, reproducible samples across both sources, selected before tuning.
EXTRA = ['cfd_final_00103.png','cfd_final_00205.png','cfd_final_00303.png',
         'cfd_final_00406.png','cfd_final_00504.png','cfd_final_00614.png',
         'cfd_final_00716.png','hf_merged_00051.png','hf_merged_00146.png',
         'hf_merged_00241.png','hf_merged_00336.png','hf_merged_00431.png',
         'hf_merged_00526.png','hf_merged_00621.png','hf_merged_00716.png',
         'hf_merged_00723.png','hf_merged_00728.png']
LOG = logging.getLogger('hair')


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f'Cannot write {path}')


def detect_points(detector, image):
    rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.face_landmarks:
        raise ValueError('no_face_detected: no mask generated; manual review required')
    h, w = image.shape[:2]
    return np.array([(p.x*w, p.y*h) for p in result.face_landmarks[0]], np.float32)


def read_skin(path, shape):
    if not path.exists():
        return None, ['skin_missing_landmark_fallback']
    skin = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if skin is None:
        return None, ['skin_unreadable_landmark_fallback']
    if skin.shape != shape:
        return None, ['skin_shape_mismatch_landmark_fallback']
    if not set(np.unique(skin)).issubset({0, 255}):
        return None, ['skin_not_binary_landmark_fallback']
    return skin, []


def segment_hair(image, points, skin=None):
    """Return binary mask and diagnostics. Input arrays are never modified.

    The dataset skin masks are a repeated template, not image-specific labels.
    Trust them only inside the detected face; the landmark oval protects eyes,
    mouth and skin elsewhere inside the face. Never subtract template pixels
    outside the face (they can be real side hair).
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError('Expected a uint8 BGR image')
    if points.shape[0] < 455 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError('Expected finite Face Landmarker pixel coordinates')
    if skin is not None and skin.shape != image.shape[:2]:
        raise ValueError('Skin dimensions do not match image')
    h, w = image.shape[:2]
    yy, xx = np.mgrid[:h,:w]
    face = np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(points[FACE_OVAL]).astype(np.int32)],255)
    left, right = sorted([float(points[234,0]),float(points[454,0])])
    fw = max(12., right-left)
    forehead, chin = float(points[10,1]),float(points[152,1])
    fh = max(12.,chin-forehead)
    cx = (left+right)/2
    # Wide side corridors preserve long and voluminous hair. Lower central
    # torso is excluded independently of its color.
    candidate = (np.abs(xx-cx) < .98*fw) & (face == 0)
    central_torso = (yy > chin-.05*fh) & (xx>left+.10*fw) & (xx<right-.10*fw)
    candidate &= ~central_torso
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    # Background samples come from upper lateral edges, never bottom corners
    # (the bottom corners often contain clothes or long hair).
    edge = ((xx < max(2,int(.025*w))) | (xx >= w-max(2,int(.025*w)))) & (yy < max(8,chin*.9))
    cv2.setRNGSeed(17)
    samples = lab[edge]
    # Robust distance to each side separately handles asymmetric backgrounds.
    centers = []
    for side in (xx<cx,xx>=cx):
        pixels = lab[edge & side]
        studio = pixels[(pixels[:,0]>230)&(np.linalg.norm(pixels[:,1:]-128,axis=1)<18)]
        # A substantial neutral bright edge cluster is a studio backdrop.
        # Otherwise use the observed edge color and flag ambiguity below.
        centers.append(np.median(studio if len(studio)>len(pixels)*.12 else pixels,axis=0))
    bg_dist = np.minimum(*[np.linalg.norm(lab-c,axis=2) for c in centers])
    bg_spread = np.median(np.min(np.stack([np.linalg.norm(samples-c,axis=1) for c in centers]),axis=0))
    bg_like = bg_dist < np.clip(2.5*bg_spread, 10, 28)
    # Only border-connected color matches are reliable background.
    n, labels = cv2.connectedComponents(bg_like.astype(np.uint8),8)
    border_labels = np.unique(labels[edge & bg_like])
    background = np.isin(labels,border_labels[border_labels != 0])
    # Learn skin appearance from small, interior landmark patches. Grow only
    # near the face, preventing the repeated template from erasing side hair.
    skin_samples = np.zeros((h,w),np.uint8)
    for index in (151, 50, 280):
        cv2.circle(skin_samples,tuple(np.rint(points[index]).astype(int)),max(2,int(.035*fw)),255,-1)
    values = lab[(skin_samples>0)&(face>0)]
    _, _, skin_centers = cv2.kmeans(values,3,None,
        (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,30,.2),3,cv2.KMEANS_PP_CENTERS)
    skin_distance = np.min(np.stack([np.linalg.norm(lab-c,axis=2) for c in skin_centers]),axis=0)
    radius = max(3,int(.40*fw))|1
    near_face = cv2.dilate(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius,radius)))>0
    skin_chroma = np.min(np.stack([np.linalg.norm(lab[:,:,1:]-c[1:],axis=2) for c in skin_centers]),axis=0)
    shadow_skin = (skin_chroma<11) & (lab[:,:,0]>np.min(skin_centers[:,0])-65)
    forehead_extension = (yy > forehead-.14*fh) & (yy < forehead+.12*fh) & (xx>left+.12*fw) & (xx<right-.12*fw)
    adaptive_skin = ((skin_distance<22)|(shadow_skin & forehead_extension)) & near_face
    candidate &= ~adaptive_skin
    upper = (yy < forehead+.12*fh) & (yy > forehead-.55*fh)
    side_anchor = (yy < forehead+.60*fh) & ((xx<left)|(xx>right))
    seeds = candidate & (upper|side_anchor) & ~background & (bg_dist>18)
    # Erosion applies to seeds only, never to the final hair silhouette.
    seeds = cv2.erode(seeds.astype(np.uint8),np.ones((3,3),np.uint8)) > 0
    if np.count_nonzero(seeds)<20:
        raise ValueError('insufficient_hair_seeds: bald/ambiguous head; manual review required')
    # Hair color is multimodal: cluster upper and side evidence, rather than
    # force every strand to match one dark crown color.
    cv2.setRNGSeed(17)
    colors = lab[seeds]
    _, _, centers_h = cv2.kmeans(colors, min(5,len(colors)), None,
                                (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,40,.2),
                                3, cv2.KMEANS_PP_CENTERS)
    color_distance = np.min(np.stack([np.linalg.norm(lab-c,axis=2) for c in centers_h]),axis=0)
    seed_distance = color_distance[seeds]
    tolerance = float(np.clip(np.percentile(seed_distance,95)*1.6,18,42))
    compatible = color_distance < tolerance
    # A lower column needs observed hair beside the face. This stops gray
    # shirts becoming foreground through a broad rectangular initialization.
    support_band = (yy>forehead+.62*fh) & (yy<forehead+.82*fh)
    support = (np.sum(candidate & compatible & ~background & support_band,axis=0) > .07*fh).astype(np.uint8)[None,:]
    support = cv2.dilate(support,np.ones((1,max(3,int(.18*fw))|1),np.uint8))[0]>0
    lower = yy > forehead+.85*fh
    candidate &= ~(lower & (~support[None,:] | ~compatible))
    gc = np.full((h,w),cv2.GC_BGD,np.uint8)
    gc[candidate & ~background] = cv2.GC_PR_BGD
    gc[candidate & ~background & compatible] = cv2.GC_PR_FGD
    gc[seeds] = cv2.GC_FGD
    # Leave the image boundary available: hair may touch the top or sides.
    # Exclude supplied skin only where anatomically supported.
    trusted_skin = np.zeros((h,w),bool) if skin is None else (skin>127)&(face>0)
    gc[(face>0)|trusted_skin] = cv2.GC_BGD
    cv2.grabCut(image,gc,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),5,cv2.GC_INIT_WITH_MASK)
    raw = ((gc==cv2.GC_FGD)|(gc==cv2.GC_PR_FGD)) & candidate
    count, cc, stats, _ = cv2.connectedComponentsWithStats(raw.astype(np.uint8),8)
    keep = np.zeros((h,w),np.uint8)
    for i in range(1,count):
        region = cc==i
        # Independent side anchors are allowed; no crown connectivity rule.
        anchored = np.any(region & (upper | ((yy < forehead+.78*fh) & ((xx<left)|(xx>right)))) & compatible)
        if stats[i,cv2.CC_STAT_AREA] >= max(8,int(h*w*.0003)) and anchored:
            keep[region] = 255
    keep[(face>0)|trusted_skin] = 0
    area = int(np.count_nonzero(keep))
    flags = []
    if area < h*w*.005: flags.append('very_small_hair_area')
    if area > h*w*.45: flags.append('large_hair_area')
    if np.any(keep[-1]): flags.append('hair_reaches_bottom_review_clothing')
    if bg_spread > 20: flags.append('complex_background_review')
    if np.mean(lab[seeds,0]>220)>.05: flags.append('bright_seeds_review_background_or_blond')
    if skin is not None: flags.append('skin_template_used_only_inside_face')
    return keep, {'hair_pixels':area,'hair_area_ratio':area/(h*w),
                  'components':cv2.connectedComponents(keep,8)[0]-1,
                  'skin_overlap_ratio':float(np.count_nonzero((keep>0)&(skin>127))/max(1,area)) if skin is not None else '',
                  'trusted_skin_overlap_ratio':float(np.count_nonzero((keep>0)&trusted_skin)/max(1,area)),
                  'face_overlap_ratio':float(np.count_nonzero((keep>0)&(face>0))/max(1,area)),
                  'flags':flags}


def labelled(image, text):
    tile=cv2.copyMakeBorder(image,25,0,0,0,cv2.BORDER_CONSTANT,value=(35,35,35))
    cv2.putText(tile,text,(5,17),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1,cv2.LINE_AA)
    return tile


def baseline_mask(image, skin, points, source):
    """Execute the archived, unchanged algorithm's segmentation section only."""
    text=source.read_text(encoding='utf-8')
    start=text.index('FACE_OVAL =')
    end=text.index('# 8. HI')
    namespace={'np':np,'cv2':cv2,'image':image,'skin':skin if skin is not None else np.zeros(image.shape[:2],np.uint8),
               'points':points,'h':image.shape[0],'w':image.shape[1]}
    cv2.setRNGSeed(17)
    exec(compile(text[start:end],str(source),'exec'),namespace)
    return namespace['hair_mask']


def save_csv(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image',nargs='+',help='One or more dataset image basenames')
    group.add_argument('--test',action='store_true',help='Three regressions + diverse fixed samples + missing skin cases')
    group.add_argument('--all',action='store_true',help='Explicitly process entire dataset (never automatic)')
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--model',type=Path,default=ROOT/'models/face_landmarker.task')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/B_color/hair_masks')
    parser.add_argument('--evaluation-dir',type=Path,default=ROOT/'outputs/B_color/hair_evaluation')
    args=parser.parse_args(argv)
    # Output directories cannot overlap source directories, including symlinks.
    sources=[(args.dataset/sub).resolve() for sub in ('images','skin_masks')]
    for dest in (args.output_dir.resolve(),args.evaluation_dir.resolve()):
        if any(dest==src or src in dest.parents or dest in src.parents for src in sources):
            parser.error('Output directories must be separate from dataset inputs')
    if args.image and any(Path(n).name!=n for n in args.image):
        parser.error('--image accepts basenames only; use --dataset to select a dataset')
    args.evaluation_dir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(args.evaluation_dir/'run.log',encoding='utf-8')])
    names=sorted(p.name for p in (args.dataset/'images').glob('*.png')) if args.all else (TARGETS+EXTRA if args.test else args.image)
    options=mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),running_mode=mp.tasks.vision.RunningMode.IMAGE,num_faces=1)
    rows=[]; failures=[]; tiles=[]
    baseline_source=args.evaluation_dir/'baseline_source.py'
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
        for name in names:
            row={'image':name}
            try:
                path=args.dataset/'images'/name
                before_hash=hashlib.sha256(path.read_bytes()).hexdigest()
                image=cv2.imread(str(path))
                if image is None: raise ValueError('image_unreadable')
                skin,warnings=read_skin(args.dataset/'skin_masks'/(path.stem+'_skin.png'),image.shape[:2])
                points=detect_points(detector,image)
                mask,info=segment_hair(image,points,skin)
                row.update(info)
                row['flags']=';'.join(warnings+info['flags'])
                row['status']='review' if row['flags'] else 'success'
                hair=cv2.bitwise_and(image,image,mask=mask)
                write_image(args.output_dir/(path.stem+'_hair_mask.png'),mask)
                write_image(args.output_dir/(path.stem+'_hair.png'),hair)
                write_image(args.evaluation_dir/'originals'/name,image)
                overlay=image.copy(); overlay[mask>0]=(image[mask>0]*.5+np.array([20,220,20])*.5).astype(np.uint8)
                preview=np.hstack([labelled(image,'Original'),labelled(cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR),'Binary hair mask'),labelled(hair,'Extracted hair'),labelled(overlay,'After overlay')])
                write_image(args.evaluation_dir/'comparisons'/(path.stem+'.png'),preview)
                if baseline_source.exists():
                    try:
                        before=baseline_mask(image,skin,points,baseline_source)
                        row['before_hair_pixels']=int(np.count_nonzero(before))
                        old=cv2.bitwise_and(image,image,mask=before)
                        comparison=np.hstack([labelled(image,name),labelled(old,'Before'),labelled(hair,'After')])
                        write_image(args.evaluation_dir/'before_after'/name,comparison)
                    except (ValueError,RuntimeError,cv2.error) as e:
                        row['baseline_error']=str(e)
                if hashlib.sha256(path.read_bytes()).hexdigest()!=before_hash: raise RuntimeError('source_changed')
                tiles.append(labelled(cv2.resize(np.hstack([image,hair]),(384,192)),name))
                LOG.info('%s %s pixels=%s flags=%s',name,row['status'],info['hair_pixels'],row['flags'])
            except (OSError,ValueError,RuntimeError,cv2.error) as e:
                row.update(status='failed',error=str(e))
                failures.append({'image':name,'reason':str(e)})
                LOG.error('%s failed: %s',name,e)
            rows.append(row)
    fields=['image','status','hair_pixels','hair_area_ratio','components','skin_overlap_ratio','trusted_skin_overlap_ratio','face_overlap_ratio','before_hair_pixels','flags','error','baseline_error']
    save_csv(args.evaluation_dir/'quality_report.csv',rows,fields)
    save_csv(args.evaluation_dir/'failed_images.csv',failures,['image','reason'])
    save_csv(args.evaluation_dir/'abnormal_images.csv',[r for r in rows if r['status']!='success'],fields)
    if tiles:
        while len(tiles)%3: tiles.append(np.zeros_like(tiles[0]))
        write_image(args.evaluation_dir/'test_contact_sheet.png',np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]))
    (args.evaluation_dir/'run_manifest.json').write_text(json.dumps({'images':names,'dataset':str(args.dataset),'model':str(args.model),'failures':len(failures),'opencv':cv2.__version__,'mediapipe':mp.__version__},indent=2),encoding='utf-8')
    return 1 if failures else 0


if __name__=='__main__':
    raise SystemExit(main())
