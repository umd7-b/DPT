"""Conservative color-sampling ROI proposal. NOT calibrated confidence or GT."""
import argparse
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import mediapipe as mp
import numpy as np

from features.B_color.src.mask_labels import DATASET, ROOT, WORK, binary_mask, overlay, safe_destination, tile, write_csv, write_image
from features.B_color.src.refine_hair_mask import FACE_OVAL, detect_points


def color_core(image, hair, points):
    h, w = hair.shape
    yy, xx = np.mgrid[:h,:w]
    face = np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(points[FACE_OVAL]).astype(np.int32)],255)
    fw = max(12,float(abs(points[454,0]-points[234,0])))
    forehead, chin = points[10,1], points[152,1]
    left, right = sorted((points[234,0],points[454,0]))
    margin = max(2,int(round(fw*.025)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*margin+1,2*margin+1))
    core = cv2.erode(hair,kernel)>0
    core &= cv2.dilate(face,kernel)==0
    # Deliberately sacrifice lower hair to avoid torso/shoulders. Require either
    # crown evidence or strong spatial separation from face in upper side hair.
    allowed = (yy<forehead-.08*(chin-forehead)) | (
        (yy<forehead+.55*(chin-forehead)) & ((xx<left-.04*fw)|(xx>right+.04*fw)))
    core &= allowed
    core[:2] = False; core[-2:] = False; core[:,:2] = False; core[:,-2:] = False
    # Exclude skin-like pixels, using only image landmark patches, never GT.
    lab = cv2.cvtColor(image,cv2.COLOR_BGR2LAB).astype(np.float32)
    skin = np.zeros((h,w),np.uint8)
    for index in (151,50,280):
        cv2.circle(skin,tuple(np.rint(points[index]).astype(int)),max(2,int(.035*fw)),255,-1)
    colors = lab[(skin>0)&(face>0)]
    if len(colors):
        center = np.median(colors,axis=0)
        core &= np.linalg.norm(lab-center,axis=2)>30
    return core.astype(np.uint8)*255


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',nargs='+',required=True)
    parser.add_argument('--dataset',type=Path,default=DATASET)
    parser.add_argument('--hair-pred-dir',type=Path,default=WORK/'predictions/hair')
    parser.add_argument('--output',type=Path,default=WORK/'hair_core')
    args = parser.parse_args()
    safe_destination(args.output,args.dataset,args.hair_pred_dir)
    if any(Path(n).name!=n or '/' in n or '\\' in n for n in args.image): parser.error('Image basenames required')
    options = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(
        model_asset_path=str(ROOT/'models/face_landmarker.task')),num_faces=1)
    rows = []
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
        for name in args.image:
            row = {'filename':name,'status':'needs_human_review_not_calibrated'}
            try:
                image = cv2.imread(str(args.dataset/'images'/name))
                if image is None: raise ValueError('Unreadable image')
                stem = Path(name).stem
                hair = binary_mask(args.hair_pred_dir/f'{stem}_hair_mask.png',image.shape[:2])
                core = color_core(image,hair,detect_points(detector,image))
                pixels = int(np.count_nonzero(core))
                row.update(pred_pixels=int(np.count_nonzero(hair)),core_pixels=pixels,
                           retained_fraction=pixels/max(1,np.count_nonzero(hair)))
                if pixels < 100: row['status'] = 'abstain_insufficient_core'
                write_image(args.output/f'{stem}_hair_mask.png',core)
                write_image(args.output/f'{stem}_core_preview.png',np.hstack([
                    tile(image,name),tile(overlay(image,hair,(255,80,20)),'Full prediction'),
                    tile(overlay(image,core,(0,220,0)),'Conservative ROI - REVIEW')]))
            except (ValueError,OSError,cv2.error) as error:
                row.update(status='failed',reason=str(error))
            rows.append(row)
    write_csv(args.output/'core_report.csv',rows,['filename','status','reason','pred_pixels','core_pixels','retained_fraction'])
    print(rows)


if __name__ == '__main__':
    main()
