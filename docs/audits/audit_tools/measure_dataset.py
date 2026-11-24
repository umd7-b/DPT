"""Non-destructive dataset measurements; model outputs are screening evidence."""
from common import *
from collections import Counter
import struct
import time
import cv2
import mediapipe as mp

metadata = read(DATA/'metadata.csv')
paths = sorted((DATA/'images').glob('*.png'))
index = {row['filename']:row for row in metadata}
assert set(index) == {p.name for p in paths}
records = []
point_samples = {}
all_points = np.zeros((len(paths),478,2),np.float32)
started = time.perf_counter()
options = mp.tasks.vision.FaceLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=str(ROOT/'models/face_landmarker.task')),
    running_mode=mp.tasks.vision.RunningMode.IMAGE, num_faces=5,
    output_facial_transformation_matrixes=True)
with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
    for n,path in enumerate(paths):
        row=index[path.name]
        content=path.read_bytes()
        assert hashlib.sha256(content).hexdigest()==row['sha256']
        assert content[:8]==b'\x89PNG\r\n\x1a\n'
        width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',content[16:29])
        image=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
        assert image is not None
        result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))))
        record=dict(image_name=path.name,source=row['source'],width=width,height=height,
            bit_depth=depth,png_color_type=color,dtype=str(image.dtype),sha256_match=True,
            model_face_count=len(result.face_landmarks),roll_deg='',ipd_percent_width='',
            eye_center_y_percent='',eye_center_x_percent='',mesh_height_percent='',
            model_euler_x='',model_euler_y='',model_euler_z='',iris_ipd_percent_width='',
            iris_eye_center_y_percent='',iris_roll_deg='',landmark_count=0,review_reasons='')
        reasons=[]
        if len(result.face_landmarks)!=1: reasons.append('model_face_count_not_one')
        if result.face_landmarks:
            p=np.array([[lm.x*width,lm.y*height] for lm in result.face_landmarks[0]],dtype=np.float64)
            record['landmark_count']=len(p)
            all_points[n]=p
            pupil_left,pupil_right=p[468],p[473]
            record.update(iris_ipd_percent_width=float(np.linalg.norm(pupil_left-pupil_right)/width*100),
                iris_eye_center_y_percent=float((pupil_left[1]+pupil_right[1])/2/height*100),
                iris_roll_deg=float(np.degrees(np.arctan2(pupil_right[1]-pupil_left[1],pupil_right[0]-pupil_left[0]))))
            left=p[[33,160,158,133,153,144]].mean(axis=0)
            right=p[[362,385,387,263,373,380]].mean(axis=0)
            ec=(left+right)/2
            ipd=float(np.linalg.norm(left-right))/width*100
            roll=float(np.degrees(np.arctan2(right[1]-left[1],right[0]-left[0])))
            angles=cv2.RQDecomp3x3(np.asarray(result.facial_transformation_matrixes[0])[:3,:3])[0]
            record.update(roll_deg=roll,ipd_percent_width=ipd,
                eye_center_y_percent=float(ec[1]/height*100),eye_center_x_percent=float(ec[0]/width*100),
                mesh_height_percent=float((p[:,1].max()-p[:,1].min())/height*100),
                model_euler_x=float(angles[0]),model_euler_y=float(angles[1]),model_euler_z=float(angles[2]))
            if abs(roll)>5: reasons.append('predicted_2D_roll_abs_gt_5')
            if abs(angles[0])>5 or abs(angles[1])>5: reasons.append('uncalibrated_model_euler_abs_gt_5')
            if ipd<27.23 or ipd>32.61: reasons.append('predicted_IPD_outside_PDF_range')
            if abs(ec[1]/height*100-40)>2: reasons.append('predicted_eye_y_farther_than_2pp_from_40')
            if record['mesh_height_percent']<70 or record['mesh_height_percent']>90:
                reasons.append('mesh_height_proxy_outside_70_90')
            if path.name in {'hf_merged_00313.png','hf_merged_00333.png','hf_merged_00561.png',
                              'hf_merged_00610.png','hf_merged_00694.png','hf_merged_00722.png'}:
                point_samples[path.name]=p.tolist()
        record['review_reasons']=';'.join(reasons)
        records.append(record)
        if (n+1)%150==0: print(f'Dataset measured {n+1}/{len(paths)}',flush=True)
csv_out('dataset_measurements.csv',records)
csv_out('dataset_model_review_candidates.csv',[r for r in records if r['review_reasons']])
dump('dataset_sample_landmarks478.json',point_samples)
np.savez_compressed(EVIDENCE/'dataset_landmarks478.npz',image_names=np.array([p.name for p in paths]),points=all_points)
valid=[r for r in records if r['ipd_percent_width']!='']
stats={key:dict(min=float(min(r[key] for r in valid)),median=float(np.median([r[key] for r in valid])),
                max=float(max(r[key] for r in valid)))
       for key in ('roll_deg','ipd_percent_width','eye_center_y_percent','eye_center_x_percent','mesh_height_percent',
                   'iris_ipd_percent_width','iris_eye_center_y_percent','iris_roll_deg')}
source_ids=Counter((r['source'],r['source_person_id']) for r in metadata if r['source_person_id'])
summary=dict(images=len(paths),metadata_rows=len(metadata),sources=dict(Counter(r['source'] for r in metadata)),
    all_png_rgb8_256=all(r['width']==256 and r['height']==256 and r['bit_depth']==8 and r['png_color_type']==2 for r in records),
    hash_matches=len(records),duplicate_byte_hashes=len(paths)-len({row['sha256'] for row in metadata}),
    model_face_counts=dict(Counter(r['model_face_count'] for r in records)),
    landmark_counts=dict(Counter(r['landmark_count'] for r in records)),
    predicted_roll_abs_gt5=sum(abs(r['roll_deg'])>5 for r in valid),
    predicted_ipd_outside_PDF_range=sum(r['ipd_percent_width']<27.23 or r['ipd_percent_width']>32.61 for r in valid),
    measurements=stats,person_id_nonempty=sum(bool(r['source_person_id']) for r in metadata),
    source_scoped_distinct_person_ids=len(source_ids),person_id_missing=sum(not r['source_person_id'] for r in metadata),
    repeated_person_extra_rows=sum(count-1 for count in source_ids.values()),
    metadata_fields=list(metadata[0]),elapsed_seconds=time.perf_counter()-started,
    caveat='All geometry/count/pose outputs are model estimates, not ground truth; mesh height is not a calibrated face-box height. Euler angles are uncalibrated model-transform estimates. No demographic inference.')
dump('dataset_verification.json',summary)
print(json.dumps(summary,indent=2))
