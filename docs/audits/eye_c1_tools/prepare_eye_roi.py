"""Audit-only eye metadata and draft ROI geometry; no C1/C2 descriptors.

Reuses the authenticated saved 478-point archive. Does not import/run MediaPipe,
fit statistics, modify A indices, or write to accepted databases/artifacts.
"""
from pathlib import Path
import ast
from contextlib import closing
import hashlib
import json
import math
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from database import store as db
from shared.report_v2 import read_json,read_csv,write_json,save_csv

E = ROOT/'docs/audits/eye_c1_evidence'
TOOLS = Path(__file__).resolve().parent
ARCHIVE = ROOT/'docs/audits/evidence/dataset_landmarks478.npz'
GEOMETRY = ROOT/'features/A_geometry/src/geometry_features.py'
NEW_DB = ROOT/'database/data/portrait_ab_v2_eye_metadata_v1.sqlite3'
BATCH = 'eye_mean6_saved478_v1'
METHOD = 'numpy_mean6_float32_from_saved478_v1'
COORDINATE_SYSTEM = 'pixel_xy; origin=top_left; x_right; y_down; original_256x256; left_right=viewer/code'
REGIONS = ['forehead_brow','cheek_left_viewer','cheek_right_viewer','nose_mouth']
PRIORITY = ['forehead_brow','nose_mouth','cheek_left_viewer','cheek_right_viewer']


def source_groups():
    tree=ast.parse(GEOMETRY.read_text(encoding='utf-8'))
    groups={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
        and isinstance(node.value,ast.List)}
    names=['JAW','LEFT_EYEBROW','RIGHT_EYEBROW','NOSE','LEFT_EYE','RIGHT_EYE','MOUTH']
    indices=sum([groups[name] for name in names],[])
    saved=read_csv(ROOT/'docs/audits/evidence/landmark_mapping.csv')
    assert len(indices)==len(set(indices))==68
    # The CSV column names are inspected explicitly rather than inferred by row position.
    assert [int(r['index68']) for r in saved]==list(range(68))
    assert [int(r['index478']) for r in saved]==indices
    assert groups['LEFT_EYE']==[33,160,158,133,153,144]
    assert groups['RIGHT_EYE']==[362,385,387,263,373,380]
    return groups,indices


def load_archive():
    baseline=read_json(E/'baseline_before.json')
    assets=[ARCHIVE,GEOMETRY,ROOT/'docs/audits/audit_tools/measure_dataset.py',
        ROOT/'docs/audits/evidence/dataset_measurements.csv',ROOT/'models/face_landmarker.task',
        ROOT/'docs/audits/evidence/dataset_verification.json',ROOT/'docs/audits/evidence/created_files_manifest.json']
    for path in assets:
        if db.digest(path)!=baseline[str(path.resolve())]:
            raise ValueError('Authenticated audit source changed: '+str(path))
    old={str((ROOT/r['path']).resolve()):r['sha256'] for r in read_json(assets[-1])['files']}
    if db.digest(ARCHIVE)!=old[str(ARCHIVE.resolve())]:
        raise ValueError('Landmark archive fails original audit manifest')
    with np.load(ARCHIVE,allow_pickle=False) as saved:
        names=saved['image_names'].tolist()
        points=saved['points'].copy()
    if len(names)!=1438 or len(set(names))!=1438 or points.shape!=(1438,478,2) or points.dtype!=np.float32:
        raise ValueError('Unexpected saved landmark shape/dtype/identity set')
    measurements={r['image_name']:r for r in read_csv(assets[3])}
    with closing(db.connect()) as c:
        images={r['filename']:dict(r) for r in c.execute('SELECT * FROM Images')}
    if set(names)!=set(images) or set(names)!=set(measurements):
        raise ValueError('Archive, audit measurement log and database image sets differ')
    for name in names:
        image=images[name]
        if (db.digest(image['image_path'])!=image['image_hash']
                or db.digest(image['image_path'])!=baseline[str(Path(image['image_path']).resolve())]):
            raise ValueError('Measured image changed: '+name)
    groups,indices=source_groups()
    proof=dict(archive=str(ARCHIVE),archive_sha256=db.digest(ARCHIVE),shape=list(points.shape),dtype=points.dtype.str,
        original_audit_manifest_sha256=db.digest(assets[-1]),measurement_script_sha256=db.digest(assets[2]),
        measurement_csv_sha256=db.digest(assets[3]),geometry_source_sha256=db.digest(GEOMETRY),
        model_version='face_landmarker.task:sha256:'+db.digest(assets[4]),model_sha256=db.digest(assets[4]),
        extraction_options=dict(running_mode='IMAGE',num_faces=5,selected_face_index=0,
            output_facial_transformation_matrixes=True),
        original_mediapipe_distribution_version=None,
        distribution_version_caveat='Full archive producer did not record package version; model asset hash is authenticated.',
        reran_mediapipe=False,measurement_role='audit_remeasurement',
        original_alignment_coordinates_verified=False,indices68=indices,
        eye_indices_left=groups['LEFT_EYE'],eye_indices_right=groups['RIGHT_EYE'])
    return names,points,images,measurements,proof


def measure_eyes(points,width,height,groups):
    if points.shape!=(478,2) or points.dtype!=np.float32 or not np.isfinite(points).all() or not np.any(points):
        raise ValueError('missing/nonfinite/invalid saved landmarks')
    left=np.mean(points[groups['LEFT_EYE']],axis=0)
    right=np.mean(points[groups['RIGHT_EYE']],axis=0)
    if not (0<=left[0]<width and 0<=right[0]<width and 0<=left[1]<height and 0<=right[1]<height):
        raise ValueError('eye center outside image bounds')
    if float(np.linalg.norm(left-right))<1e-6:
        raise ValueError('inter-eye distance below existing A guard')
    return tuple(float(v) for v in np.r_[left,right])


def prepare_eye_database(names,points,images,measurements,proof):
    if NEW_DB.exists():
        raise FileExistsError('New eye metadata database already exists; never overwrite')
    db.backup(db.DEFAULT_DB,NEW_DB)
    groups,indices=source_groups()
    method=METHOD
    measured,failed=[],[]
    with closing(db.connect(NEW_DB,readonly=False)) as c:
        try:
            c.executescript('BEGIN IMMEDIATE;\n'+(TOOLS/'eye_metadata_extension.sql').read_text(encoding='utf-8'))
            db.insert_row(c,'EyeMeasurementBatches',dict(batch_id=BATCH,created_at=db.utc_now(),
                source_database_sha256=db.digest(db.DEFAULT_DB),source_archive_sha256=proof['archive_sha256'],
                eye_center_method=method,model_version=proof['model_version'],coordinate_system=COORDINATE_SYSTEM,
                provenance=db.json_text(proof)))
            for i,name in enumerate(names):
                image=images[name]
                rowhash=db.sha_bytes(points[i].tobytes(order='C'))
                try:
                    coords=measure_eyes(points[i],image['width'],image['height'],groups)
                    audit=measurements[name]
                    if int(audit['model_face_count'])!=1 or int(audit['landmark_count'])!=478:
                        raise ValueError('saved audit does not attest exactly one detected face with 478 points')
                except ValueError as error:
                    failed.append(dict(image_id=image['image_id'],image_name=name,reason=str(error)))
                    db.insert_row(c,'EyeMeasurementAttempts',dict(batch_id=BATCH,image_id=image['image_id'],
                        status='unmeasurable',reason=str(error)))
                    continue
                provenance=dict(proof,archive_row_index=i,npz_member='points',landmark_row_shape=[478,2],
                    landmark_row_dtype=points.dtype.str,landmark_row_byte_order='C',source_landmark_hash=rowhash,
                    image_sha256=image['image_hash'],image_path=image['image_path'],arithmetic='numpy.mean on float32; promote result to SQLite REAL without changing value',
                    producer_float64_was_cast_to_saved_float32=True,
                    dataset_quality_caveat='Detected count is screening, not proof of one actual face or unoccluded tissue')
                db.insert_row(c,'EyeCoordinates',dict(image_id=image['image_id'],method=method,
                    model_version=proof['model_version'],coordinate_role='audit_remeasurement',
                    left_x=coords[0],left_y=coords[1],right_x=coords[2],right_y=coords[3],
                    coordinate_frame=COORDINATE_SYSTEM,provenance_json=db.json_text(provenance)))
                db.insert_row(c,'EyeCoordinateSources',dict(image_id=image['image_id'],batch_id=BATCH,
                    eye_center_method=method,model_version=proof['model_version'],measurement_role='audit_remeasurement',
                    coordinate_system=COORDINATE_SYSTEM,source_landmark_hash=rowhash,archive_row_index=i,
                    provenance=db.json_text(provenance)))
                db.insert_row(c,'EyeMeasurementAttempts',dict(batch_id=BATCH,image_id=image['image_id'],status='measured',reason=None))
                measured.append(dict(image_id=image['image_id'],image_name=name,left_x=coords[0],left_y=coords[1],
                    right_x=coords[2],right_y=coords[3],coordinate_system=COORDINATE_SYSTEM,
                    eye_center_method=method,model_version=proof['model_version'],source_landmark_hash=rowhash,
                    measurement_role='audit_remeasurement',archive_row_index=i))
            assert not c.execute('PRAGMA foreign_key_check').fetchall()
            c.commit()
        except BaseException:
            c.rollback()
            raise  # Never overwrite/delete the original DB or an existing target.
    save_csv(E/'eye_measurements.csv',measured)
    save_csv(E/'unmeasurable_eyes.csv',failed,['image_id','image_name','reason'])
    write_json(E/'landmark_source_proof.json',proof)
    return measured,failed


def contract(indices):
    def p(i,u=0.,v=0.):
        return dict(ref='A68',index=i,mediapipe_index=indices[i],offset_u_ipd=u,offset_v_ipd=v)
    def mp(i):
        return dict(ref='MP478_AUX',index=i,mediapipe_index=i,offset_u_ipd=0.,offset_v_ipd=0.)
    upper=[127,162,21,54,103,67,109,10,338,297,332,284,251,389,356]
    polygons={
        'forehead_brow':[mp(i) for i in upper]+[p(i,v=.05) for i in range(26,16,-1)],
        'cheek_left_viewer':[p(i,v=.08) for i in [36,41,40,39]]+[p(i) for i in [31,48,5,4,3,2,1,0]],
        'cheek_right_viewer':[p(i,v=.08) for i in [45,46,47,42]]+[p(i) for i in [35,54,11,12,13,14,15,16]],
        'nose_mouth':[p(27),p(42,v=.08),p(35),p(54,u=.05)]+
            [p(i,v=.06) for i in [55,56,57,58,59]]+[p(48,u=-.05),p(31),p(39,v=.08)]}
    return dict(id='C1_ROI_PROPOSAL_v0.1',status='PROPOSAL_UNVERIFIED_NOT_FOR_FEATURE_EXTRACTION',
        pdf_region_order=['forehead_and_eyebrows','left_cheek','right_cheek','nose_and_mouth'],
        provisional_order=REGIONS,overlap_priority=PRIORITY,polygons=polygons,
        auxiliary_upper_face_oval=upper,
        side_convention='viewer/code left/right; relation to PDF anatomical frame requires approval',
        frame='u=normalized right-eye minus left-eye; v=(-u_y,u_x), positive image-y; D=inter-eye distance',
        vertex_equation='P=source_landmark + D*(offset_u_ipd*u + offset_v_ipd*v)',
        connection='straight edges in listed order; last vertex connects to first; no splines or hull',
        pixel_rule='float64 derived vertices cast to float32 contour; integer pixel centres (x,y); cv2.pointPolygonTest >=0 includes boundary',
        clipping='evaluate only 0<=x<width,0<=y<height; no clamp of vertices; no extrapolation',
        overlap_rule='assign raw membership to first region in priority; others subtract earlier assigned pixels',
        missing_rule='missing/nonfinite/degenerate/self-intersecting/empty region is invalid, never fabricated',
        future_descriptor_missing_policy='PROPOSED: any missing/invalid required region means missing_C1; no 236-vector or zero-fill; no descriptor is implemented here',
        uncovered_rule='unassigned pixels remain unassigned; do not stretch/fill the four regions',
        occlusion_rule='geometry masks do not attest visible skin; known dataset violations remain review flags',
        lbp_boundary_proposal='future LBP centre eligible only if full radius-2 support remains within assigned region; not implemented here',
        all_vertex_choices_and_offsets='IMPLEMENTATION DETAIL PROPOSED; anatomical endpoints UNVERIFIED',
        numerical_guards=dict(min_ipd_pixels=1e-6,min_polygon_area_pixels_squared=1e-6,
            min_edge_length_pixels=1e-9,segment_collinearity_and_bounds_tolerance=1e-9),
        native_topology_scope='membership in saved MediaPipe contours is verified, canonical A68 identities are not',
        indices68_unchanged=indices,c1_c2_vectors_created=False,retrieval_used_for_selection=False)


def polygon_points(points,spec,groups):
    l=points[groups['LEFT_EYE']].mean(axis=0).astype(float)
    r=points[groups['RIGHT_EYE']].mean(axis=0).astype(float)
    d=float(np.linalg.norm(r-l))
    if not np.isfinite(points).all() or d<1e-6:
        raise ValueError('invalid source points/eye frame')
    u=(r-l)/d; v=np.array([-u[1],u[0]])
    if u[0]<=0 or v[1]<=0:
        raise ValueError('unexpected left/right orientation; no automatic swap')
    return {name:np.array([points[item['mediapipe_index']].astype(float)+d*(item['offset_u_ipd']*u+item['offset_v_ipd']*v)
                          for item in vertices]) for name,vertices in spec['polygons'].items()}


def self_intersects(vertices):
    def cross(a,b,c):
        x,y=b-a; z,w=c-a
        return x*w-y*z
    n=len(vertices)
    if n<3 or any(np.linalg.norm(vertices[i]-vertices[(i+1)%n])<1e-9 for i in range(n)):
        return True
    def touches(a,b,c):
        return abs(cross(a,b,c))<=1e-9 and np.all(c>=np.minimum(a,b)-1e-9) and np.all(c<=np.maximum(a,b)+1e-9)
    for i in range(n):
        a,b=vertices[i],vertices[(i+1)%n]
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1):
                continue
            c,d=vertices[j],vertices[(j+1)%n]
            if (cross(a,b,c)*cross(a,b,d)<-1e-9 and cross(c,d,a)*cross(c,d,b)<-1e-9
                    or touches(a,b,c) or touches(a,b,d) or touches(c,d,a) or touches(c,d,b)):
                return True
    return False


def preview_masks(polygons,width,height):
    masks={}; diagnostics={}
    for name,p in polygons.items():
        if not np.isfinite(p).all() or self_intersects(p) or abs(cv2.contourArea(p.astype(np.float32)))<1e-6:
            masks[name]=None; diagnostics[name]='invalid_geometry'
            continue
        mask=np.zeros((height,width),bool)
        contour=p.astype(np.float32)
        # Bounding-box evaluation only changes speed, not integer-centre membership.
        x0=max(0,math.floor(float(p[:,0].min()))); x1=min(width-1,math.ceil(float(p[:,0].max())))
        y0=max(0,math.floor(float(p[:,1].min()))); y1=min(height-1,math.ceil(float(p[:,1].max())))
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                mask[y,x]=cv2.pointPolygonTest(contour,(float(x),float(y)),False)>=0
        masks[name]=mask if mask.any() else None
        diagnostics[name]='valid_geometry_only' if mask.any() else 'empty_region'
    assigned={}; used=np.zeros((height,width),bool)
    for name in PRIORITY:
        mask=masks[name]
        assigned[name]=None if mask is None else mask & ~used
        if mask is not None:
            used |= mask
            if not assigned[name].any():
                assigned[name]=None; diagnostics[name]='empty_after_overlap'
    overlap=sum(int((masks[a]&masks[b]).sum()) for i,a in enumerate(REGIONS) for b in REGIONS[i+1:]
        if masks[a] is not None and masks[b] is not None)
    return assigned,diagnostics,overlap


def render(name,image,points,polygons,masks,spec):
    scale=3; side=768; header=88
    canvas=np.full((side+header,side+470,3),255,np.uint8)
    photo=cv2.resize(image,(side,side),interpolation=cv2.INTER_NEAREST)
    tint=photo.copy()
    colors=dict(forehead_brow=(80,185,250),cheek_left_viewer=(70,200,80),
                cheek_right_viewer=(240,160,60),nose_mouth=(150,70,230))
    for key in REGIONS:
        if masks[key] is not None:
            enlarged=cv2.resize(masks[key].astype(np.uint8),(side,side),interpolation=cv2.INTER_NEAREST).astype(bool)
            tint[enlarged]=colors[key]
    photo=cv2.addWeighted(photo,.67,tint,.33,0)
    for key,p in polygons.items():
        q=np.rint(p*scale).astype(np.int32)
        cv2.polylines(photo,[q],True,colors[key],2,cv2.LINE_AA)
        for x,y in q:
            cv2.circle(photo,(int(x),int(y)),2,(0,0,0),-1)
    for index in [1,4]:
        x,y=np.rint(points[index]*scale).astype(int)
        cv2.circle(photo,(x,y),5,(0,0,255),1)
        cv2.putText(photo,f'MP{index}',(x+6,y),0,.45,(0,0,255),1,cv2.LINE_AA)
    canvas[header:,:side]=photo
    for y,text in [(25,name+' | C1 ROI PROPOSAL v0.1'),(49,'AUDIT ONLY: anatomical boundaries are UNVERIFIED'),
                   (72,'Saved 478 points; no detector, no LBP/C vectors, no A mapping changes')]:
        cv2.putText(canvas,text,(10,y),0,.6,(0,0,0),1,cv2.LINE_AA)
    y=header+30
    for key in REGIONS:
        cv2.putText(canvas,key,(side+12,y),0,.55,colors[key],2); y+=25
        cv2.putText(canvas,f'assigned pixels: {int(masks[key].sum()) if masks[key] is not None else "MISSING"}',
                    (side+12,y),0,.48,(0,0,0),1); y+=32
    for text in ['Overlap priority: forehead, nose-mouth,', 'viewer-left cheek, viewer-right cheek.',
                 'Unassigned pixels stay unassigned.', 'MP1/MP4 shown red, not corrected.',
                 'Counts prove geometry only.', 'Hair, hands, cloth and glasses may',
                 'remain inside proposed polygons.', 'All vertex indices/offsets: contract JSON.',
                 'This preview does not certify anatomy.']:
        cv2.putText(canvas,text,(side+12,y),0,.45,(0,0,0),1,cv2.LINE_AA); y+=24
    path=E/'overlays'/f'{Path(name).stem}_c1_roi_proposal.png'
    path.parent.mkdir(exist_ok=True)
    if not cv2.imwrite(str(path),canvas):
        raise OSError('Cannot save draft overlay')
    if name in ('cfd_final_00001.png','hf_merged_00001.png'):
        panels=[]
        for key in REGIONS:
            panel=np.full((side+70,side,3),255,np.uint8)
            panel[70:]=cv2.resize(image,(side,side),interpolation=cv2.INTER_NEAREST)
            q=np.rint(polygons[key]*scale).astype(np.int32)
            cv2.polylines(panel[70:],[q],True,colors[key],2,cv2.LINE_AA)
            for xy,item in zip(q,spec['polygons'][key]):
                x,y=map(int,xy); y+=70
                label=('A' if item['ref']=='A68' else 'M')+str(item['index'])
                if item['offset_u_ipd'] or item['offset_v_ipd']:
                    label+='*'
                cv2.circle(panel,(x,y),3,colors[key],-1)
                cv2.putText(panel,label,(x+5,y-4),0,.43,(255,255,255),3,cv2.LINE_AA)
                cv2.putText(panel,label,(x+5,y-4),0,.43,(0,0,0),1,cv2.LINE_AA)
            cv2.putText(panel,key+' | A=index68; M=MP index',(10,23),0,.55,(0,0,0),1)
            cv2.putText(panel,'* = derived offset. PROPOSAL / UNVERIFIED.',(10,50),0,.55,(0,0,0),1)
            panels.append(panel)
        labeled=np.vstack([np.hstack(panels[:2]),np.hstack(panels[2:])])
        if not cv2.imwrite(str(path.with_name(Path(name).stem+'_c1_roi_vertex_labels.png')),labeled):
            raise OSError('Cannot save labeled draft overlay')


def prepare_roi_preview(names,points,images):
    groups,indices=source_groups(); spec=contract(indices)
    native=read_json(ROOT/'docs/audits/pre_c_evidence/native_mediapipe_topology.json')
    contour_nodes={k:{i for edge in v for i in edge} for k,v in native['edges'].items()}
    assert all(i in contour_nodes['FACE_LANDMARKS_FACE_OVAL'] for i in spec['auxiliary_upper_face_oval'])
    write_json(E/'c1_roi_contract_proposal_v0.json',spec)
    cases=['cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00333.png',
           'hf_merged_00561.png','hf_merged_00722.png','hf_merged_00209.png','hf_merged_00694.png']
    metrics=[]; vertex_rows=[]
    for name in cases:
        i=names.index(name); image=images[name]
        polygons=polygon_points(points[i],spec,groups)
        masks,diagnostics,overlap=preview_masks(polygons,image['width'],image['height'])
        nonmissing=[m for m in masks.values() if m is not None]
        assert not nonmissing or np.max(np.sum(nonmissing,axis=0))<=1
        metrics.append(dict(image_name=name,geometry_status=diagnostics,raw_pairwise_overlap_pixels=overlap,
            assigned_pixels={k:None if v is None else int(v.sum()) for k,v in masks.items()},
            uncovered_pixels=image['width']*image['height']-sum(int(v.sum()) for v in nonmissing),
            semantic_anatomy_verified=False))
        for key,p in polygons.items():
            for order,(xy,item) in enumerate(zip(p,spec['polygons'][key])):
                vertex_rows.append(dict(image_name=name,region=key,vertex_order=order,
                    ref=item['ref'],index=item['index'],mediapipe_index=item['mediapipe_index'],
                    offset_u_ipd=item['offset_u_ipd'],offset_v_ipd=item['offset_v_ipd'],x=float(xy[0]),y=float(xy[1])))
        render(name,cv2.imread(image['image_path']),points[i],polygons,masks,spec)
    save_csv(E/'roi_preview_vertices.csv',vertex_rows)
    write_json(E/'roi_preview_validation.json',dict(cases=metrics,c1_c2_extracted=False,
        numpy_version=np.__version__,opencv_version=cv2.__version__,
        scope='Eight illustrative cases only; full-corpus ROI quality is not certified'))
    return metrics


def main():
    names,points,images,measurements,proof=load_archive()
    measured,failed=prepare_eye_database(names,points,images,measurements,proof)
    previews=prepare_roi_preview(names,points,images)
    assert 'mediapipe' not in sys.modules, 'This audit must not import/run MediaPipe'
    print(db.json_text(dict(measured=len(measured),unmeasurable=len(failed),new_database=str(NEW_DB),
        overlay_cases=len(previews),mediapipe_rerun=False,c1_c2_vectors_created=False)))


if __name__=='__main__':
    main()
