"""Real A/C1/C2 query adapter in .venv311; original math modules are read-only."""
import argparse
import hashlib
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from app.external_config import MODEL_SHA256
from features.A_geometry.src import geometry_features as geometry,report_v2 as a
from features.C1_lbp.src import lbp236
from features.C1_lbp.src.full_v04 import V04Context
from features.C2_hog.src import root_hog as hog
from shared.report_v2 import digest,load_stats,write_json


def native_points(bgr,max_faces):
    options=mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(geometry.MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,num_faces=max_faces)
    rgb=np.ascontiguousarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
        found=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
    return [np.array([[p.x*bgr.shape[1],p.y*bgr.shape[0]] for p in face],dtype=np.float32)
            for face in found.face_landmarks]


def extract(image,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    if digest(geometry.MODEL_PATH)!=MODEL_SHA256:raise ValueError('MediaPipe model hash mismatch')
    bgr=cv2.imread(str(image),cv2.IMREAD_UNCHANGED)
    if bgr is None or bgr.shape!=(256,256,3) or bgr.dtype!=np.uint8:raise ValueError('Expected confirmed 256x256 BGR')
    common=dict(image_sha256=digest(image),pixel_sha256=hashlib.sha256(bgr.tobytes()).hexdigest(),model_sha256=MODEL_SHA256)
    # A legacy num_faces=1 cannot establish cardinality. Additional gate uses the
    # same locked model with cap5. Main descriptor landmarks retain cap1 behavior.
    faces=native_points(bgr,5)
    status=dict(**common,face_count=len(faces),face_count_gate='same model IMAGE/cap5; descriptor IMAGE/cap1',features={})
    if len(faces)!=1:
        status.update(status='failed',missing_reason='no_face' if not faces else 'multiple_faces')
        for kind in ('a','c1','c2'):status['features'][kind]=dict(status='not_extracted',missing_reason=status['missing_reason'])
        write_json(destination/'ac_status.json',status);return status
    points=native_points(bgr,1)
    if len(points)!=1 or points[0].shape!=(478,2):raise ValueError('Descriptor landmark pass failed')
    points=points[0];np.save(destination/'landmarks478.npy',points,allow_pickle=False)
    p68=points[geometry.INDICES]
    normalized,_=geometry.normalize_landmarks(p68)
    # Identical assembly to extract_geometry; reuse its normalization and all14 ratios.
    raw=np.concatenate((normalized.flatten().astype(np.float32),geometry.calculate_ratios(p68)))
    stats_path=a.DEFAULT_OUTPUT/'normalization_stats.npz';stats=load_stats(stats_path)
    av=a.transform(raw,stats)
    np.save(destination/'query_A_raw.npy',raw,allow_pickle=False);np.save(destination/'query_A_normalized.npy',av,allow_pickle=False)
    status['features']['a']=dict(status='valid',dimension=150,dtype=av.dtype.str,schema_id=a.SCHEMA_ID,
        stats_sha256=digest(stats_path),query_refit=False,landmark_row_sha256=hashlib.sha256(points.tobytes()).hexdigest())
    c1=lbp236.Extractor(V04Context()).extract(bgr,points,'external_query','external')
    status['features']['c1']={k:v for k,v in c1.items() if k not in ('counts','histograms','vector')}
    if c1['vector'] is not None:
        np.save(destination/'query_C1.npy',c1['vector'],allow_pickle=False);np.save(destination/'counts_C1.npy',c1['counts'],allow_pickle=False)
    c2=hog.extract_c2(bgr);status['features']['c2']=dict(status=c2['status'],missing_reason=c2['missing_reason'],**hog.lock())
    if c2['vector'] is not None:np.save(destination/'query_C2.npy',c2['vector'],allow_pickle=False)
    status['status']='extracted';write_json(destination/'ac_status.json',status)
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();extract(args.image,args.output)
