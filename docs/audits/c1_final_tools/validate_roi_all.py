"""Full-dataset RAW polygon audit and LBP specification artifacts, no extractor.

Never calls the v0.1 priority-mask function, MediaPipe, or any image LBP/HOG code.
"""
from pathlib import Path
from collections import Counter,defaultdict
from contextlib import closing
import copy
import hashlib
import itertools
import json
import math
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'docs/audits/eye_c1_tools'))
import prepare_eye_roi as previous
from shared.report_v2 import read_json,read_csv,write_json,save_csv

OUT=ROOT/'outputs/C1_lbp/roi_validation'
REGIONS=previous.REGIONS
PROPOSAL=previous.E/'c1_roi_contract_proposal_v0.json'
MIN_REVIEW_PIXELS=256
MIN_TECHNICAL_SUPPORT=64
PAIR_KEYS=list(itertools.combinations(REGIONS,2))
BROW_LEFT=[70,63,105,66,107,55,65,52,53,46]
BROW_RIGHT=[336,296,334,293,300,276,283,282,295,285]
KNOWN={
    'hf_merged_00333':dict(image='secondary_faces_visible',roi={}),
    'hf_merged_00561':dict(image='secondary_face_and_forehead_hair',roi={'forehead_brow':'forehead_hair_visible'}),
    'hf_merged_00722':dict(image='hand_occludes_mouth',roi={'nose_mouth':'visible_hand_overlap'}),
    'hf_merged_00209':dict(image='head_covering;B_missing_hair',roi={}),
    'hf_merged_00694':dict(image='head_covering_and_glasses',roi={'forehead_brow':'cloth_visible;glasses_near_boundary'})}


def digest(path):
    return previous.db.digest(path)


def canonical_hash(value):
    return hashlib.sha256(previous.db.json_text(value).encode('utf-8')).hexdigest()


def write_contract():
    proposal=read_json(PROPOSAL)
    contract=dict(schema_id='C1_ROI_RAW_CONTRACT_v0.2.0',version='0.2.0',status='PROVISIONAL',
        report_sha256=previous.db.legacy.REPORT_SHA256,source_proposal_id=proposal['id'],
        source_proposal_sha256=digest(PROPOSAL),polygons=copy.deepcopy(proposal['polygons']),
        geometry_sha256=canonical_hash(proposal['polygons']),
        geometry_changed_from_v0_1=False,region_order=REGIONS,side_convention=proposal['side_convention'],
        auxiliary_upper_face_oval=proposal['auxiliary_upper_face_oval'],indices68_unchanged=proposal['indices68_unchanged'],
        frame=proposal['frame'],vertex_equation=proposal['vertex_equation'],connection=proposal['connection'],
        pixel_rule=proposal['pixel_rule'],clipping=proposal['clipping'],
        overlap_policy='RAW_INDEPENDENT_MEMBERSHIP; shared pixels remain in each region; no priority subtraction',
        priority_subtraction_applied=False,
        future_pooling='Each raw ROI pools independently; overlap ownership is not assigned to one ROI',
        missing_policy='Future C1 unavailable if any required ROI invalid or fewer than 64 support-valid centres; no zero-fill',
        numerical_guards=proposal['numerical_guards'],
        technical_review_thresholds=dict(raw_pixels_lt=MIN_REVIEW_PIXELS,support_centres_lt=MIN_TECHNICAL_SUPPORT,
            authority='Implementation conventions selected before full-dataset metrics; not PDF quality thresholds'),
        anatomical_validation='UNVERIFIED; native-contour and eyebrow proxies are not manual anatomical ground truth',
        modifications_proposed_but_not_active=['Forehead lower boundary from native lower-eyebrow chain +0.02 IPD'],
        extractor_implemented=False,c1_c2_vectors_created=False,retrieval_used_to_choose_roi=False)
    contract['content_sha256']=canonical_hash(contract)
    write_json(OUT/'contract_v0_2.json',contract)
    (OUT/'contract_v0_2.sha256').write_text(digest(OUT/'contract_v0_2.json')+'  contract_v0_2.json\n',encoding='utf-8')
    return contract


def raw_mask(vertices,width=256,height=256):
    """Exact v0.1 point-at-integer-centre rule, without assigning overlap."""
    mask=np.zeros((height,width),np.uint8)
    if not np.isfinite(vertices).all():
        return mask
    contour=np.asarray(vertices,np.float32)
    x0=max(0,math.floor(float(vertices[:,0].min())))
    x1=min(width-1,math.ceil(float(vertices[:,0].max())))
    y0=max(0,math.floor(float(vertices[:,1].min())))
    y1=min(height-1,math.ceil(float(vertices[:,1].max())))
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            mask[y,x]=cv2.pointPolygonTest(contour,(float(x),float(y)),False)>=0
    return mask


def support_footprint():
    # Geometry only: union of the bilinear integer stencils, not image samples.
    q=math.sqrt(2)
    offsets=[(2.,0.),(q,-q),(0.,-2.),(-q,-q),(-2.,0.),(-q,q),(0.,2.),(q,q)]
    points={(0,0)}
    for x,y in offsets:
        for dx in {math.floor(x),math.ceil(x)}:
            for dy in {math.floor(y),math.ceil(y)}:
                points.add((dx,dy))
    return sorted(points,key=lambda p:(p[1],p[0]))


def support_centres(mask):
    kernel=np.zeros((5,5),np.uint8)
    for dx,dy in support_footprint():
        kernel[dy+2,dx+2]=1
    return cv2.erode(mask,kernel,anchor=(2,2),borderType=cv2.BORDER_CONSTANT,borderValue=0)


def face_oval_order(native):
    edges=native['edges']['FACE_LANDMARKS_FACE_OVAL']
    neighbours=defaultdict(list)
    for a,b in edges:
        neighbours[a].append(b);neighbours[b].append(a)
    assert all(len(v)==2 for v in neighbours.values())
    order=[10,338]
    while True:
        next_point=next(i for i in neighbours[order[-1]] if i!=order[-2])
        if next_point==10:
            break
        assert next_point not in order
        order.append(next_point)
    assert len(order)==len(neighbours)
    return order


def stats(values):
    x=np.asarray(values,float)
    return dict(min=float(x.min()),p01=float(np.quantile(x,.01)),median=float(np.median(x)),
        mean=float(x.mean()),p99=float(np.quantile(x,.99)),max=float(x.max()))


def codebook_rows():
    """Enumerate bit-word labels for the specification; no image LBP operation."""
    result=[]
    for code in range(256):
        bits=[(code>>p)&1 for p in range(8)]
        transitions=sum(bits[p]!=bits[(p+1)%8] for p in range(8))
        ones=sum(bits)
        if transitions>2:
            label=58; start=None
        elif ones==0:
            label=0; start=None
        elif ones==8:
            label=57;start=None
        else:
            start=next(p for p in range(8) if bits[p] and not bits[(p-1)%8])
            label=1+8*(ones-1)+((-start)%8)
        result.append(dict(raw_code=code,bits_p0_to_p7=''.join(map(str,bits)),
            circular_transitions=transitions,ones=ones,run_start=start,nri_uniform_bin=label))
    return result


def lbp_specification(contract):
    spec=dict(schema_id='C1_LBP_236_IMPLEMENTATION_SPEC_v0.1.0',version='0.1.0',status='SPEC_ONLY_PROVISIONAL_ROI',
        report_sha256=previous.db.legacy.REPORT_SHA256,roi_contract_id=contract['schema_id'],
        roi_contract_content_sha256=contract['content_sha256'],roi_contract_file_sha256=digest(OUT/'contract_v0_2.json'),
        pdf_requirements=dict(P=8,R=2,threshold='g_p >= g_c; no epsilon in bit test',
            uniform='circular transitions <=2; non-rotation-invariant',bins=59,regions=4,dimension=236,
            per_region_normalization='L1',distance='0.5*sum((h1-h2)^2/(h1+h2+epsilon))'),
        conventions=dict(grayscale='gray_uint8=floor((1868*B+9617*G+4899*R+8192)/16384); uint32 accumulation, then float64 interpolation',
            grayscale_coefficients_bgr=[1868,9617,4899],grayscale_denominator=16384,grayscale_rounding_bias=8192,
            interpolation='float64 bilinear via horizontal lerp then vertical lerp; no intensity rounding or padding',
            offsets_xy=['(2,0)','(sqrt(2),-sqrt(2))','(0,-2)','(-sqrt(2),-sqrt(2))',
                        '(-2,0)','(-sqrt(2),sqrt(2))','(0,2)','(sqrt(2),sqrt(2))'],
            bit_order='p0 east; counterclockwise on displayed image; p contributes 2**p',
            bin_mapping='0 word ->0; 255 word ->57; nonuniform ->58; otherwise 1+8*(ones-1)+((-run_start)%8)',
            support='centre plus every nonzero-weight bilinear stencil pixel must be inside same raw ROI and image',
            support_footprint_xy=support_footprint(),overlap='retain shared pixels independently; no priority subtraction',
            min_eligible_centres=64,missing='any required region invalid/small -> missing_C1; no 236-vector or zero-fill',
            concatenation=REGIONS,histogram='uint64 counts, divide float64 by integer eligible count; no epsilon L1',
            nonfinite='reject image/landmarks/interpolation/histogram; no nan_to_num, imputation or clipping',
            distance_epsilon=1e-8,dtype='float64 C1 after per-region L1; no added feature or refit A/B',
            new_query='same aligned 256x256 RGB input, pinned geometry/grayscale/codebook/support; explicit missing state'),
        provenance=dict(nri_definition='PDF; technical terminology cross-check only: scikit-image 0.25.2 documentation',
            label_numbering_reference='https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/feature/_texture.pyx',
            full_backend_equivalence_claimed=False,
            backend_caveat='scikit-image rounds neighbour coordinates to 5 decimals and has its own border/interpolation arithmetic; this specification does not blindly delegate those conventions'),
        extractor_implemented=False,lbp_codes_computed_on_images=False,feature_vectors_created=False)
    spec['content_sha256']=canonical_hash(spec)
    write_json(OUT/'lbp_implementation_spec.json',spec)
    save_csv(OUT/'nri_uniform_59_codebook.csv',codebook_rows())
    return spec


def main():
    if (OUT/'summary.json').exists():
        raise FileExistsError('Completed validation output exists; do not overwrite')
    baseline=read_json(OUT/'baseline_before.json')
    assert all(digest(p)==h for p,h in baseline.items())
    names,points,images,measurements,proof=previous.load_archive()
    groups,indices=previous.source_groups()
    contract=write_contract(); lbp_specification(contract)
    native=read_json(ROOT/'docs/audits/pre_c_evidence/native_mediapipe_topology.json')
    oval=face_oval_order(native)
    edge_set={frozenset(e) for e in native['edges']['FACE_LANDMARKS_FACE_OVAL']}
    upper=contract['auxiliary_upper_face_oval']
    assert all(frozenset(e) in edge_set for e in zip(upper,upper[1:]))
    manifest={r['image_id']:r for r in read_csv(previous.db.b_v2.DEFAULT_OUTPUT/'manifest.csv')}
    roi_rows=[]; image_rows=[]; overlap_rows=[]; vertex_rows=[]
    for i,name in enumerate(names):
        image=images[name];identity=image['image_id'];p=points[i]
        source=cv2.imread(image['image_path'],cv2.IMREAD_UNCHANGED)
        if source is None or source.shape!=(256,256,3) or source.dtype!=np.uint8:
            raise ValueError('Unexpected source image '+name)
        entry=manifest[identity]
        if digest(entry['hair_mask_path'])!=entry['hair_mask_sha256']:
            raise ValueError('Frozen hair-mask hash mismatch')
        hair=cv2.imread(entry['hair_mask_path'],cv2.IMREAD_GRAYSCALE)
        if hair is None or hair.shape!=(256,256) or not set(np.unique(hair)).issubset({0,255}):
            raise ValueError('Invalid saved raw hair mask')
        hair=hair!=0
        polygons=previous.polygon_points(p,contract,groups)
        masks={key:raw_mask(v) for key,v in polygons.items()}
        count=np.sum(np.stack(list(masks.values())),axis=0)
        face=raw_mask(p[oval].astype(float)).astype(bool)
        union=count>0
        gaps=face & ~union
        boundary=face & ~cv2.erode(face.astype(np.uint8),np.ones((3,3),np.uint8),borderType=cv2.BORDER_CONSTANT,borderValue=0).astype(bool)
        n,labels,components,_=cv2.connectedComponentsWithStats(gaps.astype(np.uint8),connectivity=8)
        enclosed=[int(components[j,cv2.CC_STAT_AREA]) for j in range(1,n) if not np.any(boundary & (labels==j))]
        brow_proxy=np.maximum(raw_mask(p[BROW_LEFT]),raw_mask(p[BROW_RIGHT])).astype(bool)
        forehead=polygons['forehead_brow'].astype(np.float32)
        a_brow_inside=sum(cv2.pointPolygonTest(forehead,tuple(map(float,p[j])),False)>=0 for j in indices[17:27])
        native_inside=sum(cv2.pointPolygonTest(forehead,tuple(map(float,p[j])),False)>=0 for j in BROW_LEFT+BROW_RIGHT)
        brow_pixels=int(brow_proxy.sum()); brow_covered=int((brow_proxy & (masks['forehead_brow']!=0)).sum())
        risk=KNOWN.get(identity,dict(image='UNVERIFIED',roi={}))
        for region in REGIONS:
            v=polygons[region];mask=masks[region];finite=bool(np.isfinite(v).all())
            intersection=previous.self_intersects(v) if finite else True
            area=abs(float(cv2.contourArea(v.astype(np.float32)))) if finite else 0.
            signed=float(.5*np.sum(v[:,0]*np.roll(v[:,1],-1)-np.roll(v[:,0],-1)*v[:,1])) if finite else 0.
            raw_pixels=int(mask.sum());eligible=int(support_centres(mask).sum())
            outside=int(np.sum((v[:,0]<0)|(v[:,0]>255)|(v[:,1]<0)|(v[:,1]>255))) if finite else len(v)
            reasons=[]
            expected=len(contract['polygons'][region])
            if len(v)!=expected:reasons.append('vertex_count_mismatch')
            if not finite:reasons.append('nonfinite')
            if intersection:reasons.append('self_intersection_or_zero_edge')
            if area<1e-6:reasons.append('zero_or_numerically_degenerate_area')
            if raw_pixels==0:reasons.append('empty_clipped_mask')
            valid=not reasons
            geometry_warnings=[]
            if outside:geometry_warnings.append('vertices_outside_image')
            if raw_pixels<MIN_REVIEW_PIXELS:geometry_warnings.append('raw_mask_lt_256_review')
            if eligible<MIN_TECHNICAL_SUPPORT:geometry_warnings.append('support_centres_lt_64')
            roi_rows.append(dict(image_id=identity,image_name=name,source=image['source'],region=region,
                vertex_count=len(v),expected_vertex_count=expected,vertex_sequence_preserved=True,
                finite_coordinates=finite,self_intersection=intersection,continuous_area_px2=area,signed_area_px2=signed,
                min_x=float(v[:,0].min()),max_x=float(v[:,0].max()),min_y=float(v[:,1].min()),max_y=float(v[:,1].max()),
                vertices_outside_image=outside,raw_mask_pixels=raw_pixels,support_valid_centres=eligible,
                raw_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),geometry_valid=valid,
                geometry_invalid_reasons=';'.join(reasons),geometry_warnings=';'.join(geometry_warnings),
                too_small_review=raw_pixels<MIN_REVIEW_PIXELS or eligible<MIN_TECHNICAL_SUPPORT,
                predicted_hair_overlap_pixels=int((mask.astype(bool)&hair).sum()),
                predicted_hair_overlap_fraction=float((mask.astype(bool)&hair).sum()/raw_pixels) if raw_pixels else None,
                hair_proxy_status='SAVED_MODEL_OUTPUT_NOT_GT',anatomical_status='UNVERIFIED',
                hand_glasses_cloth_status=risk['roi'].get(region,'UNVERIFIED'),
                a68_brow_points_inside=a_brow_inside if region=='forehead_brow' else None,
                native_brow_points_inside=native_inside if region=='forehead_brow' else None,
                native_brow_proxy_pixels=brow_pixels if region=='forehead_brow' else None,
                native_brow_proxy_covered_pixels=brow_covered if region=='forehead_brow' else None,
                native_brow_proxy_coverage=float(brow_covered/brow_pixels) if region=='forehead_brow' and brow_pixels else None))
            for j,(xy,ref) in enumerate(zip(v,contract['polygons'][region])):
                vertex_rows.append(dict(image_id=identity,region=region,vertex_order=j,ref=ref['ref'],
                    source_index=ref['index'],mediapipe_index=ref['mediapipe_index'],offset_u_ipd=ref['offset_u_ipd'],
                    offset_v_ipd=ref['offset_v_ipd'],x=float(xy[0]),y=float(xy[1])))
        for a,b in PAIR_KEYS:
            ma,mb=masks[a].astype(bool),masks[b].astype(bool)
            overlap=int((ma&mb).sum()); total=int((ma|mb).sum())
            overlap_rows.append(dict(image_id=identity,region_a=a,region_b=b,overlap_pixels=overlap,
                union_pixels=total,jaccard=float(overlap/total) if total else 0.))
        eye_proxy=np.maximum(raw_mask(p[indices[36:42]]),raw_mask(p[indices[42:48]])).astype(bool)
        image_rows.append(dict(image_id=identity,image_name=name,source=image['source'],face_oval_pixels=int(face.sum()),
            raw_union_pixels=int(union.sum()),overlap_unique_pixels=int((count>=2).sum()),max_memberships=int(count.max()),
            unassigned_image_pixels=int((~union).sum()),unassigned_face_pixels=int(gaps.sum()),
            unassigned_eye_proxy_pixels=int((gaps&eye_proxy).sum()),
            unassigned_non_eye_face_pixels=int((gaps&~eye_proxy).sum()),
            enclosed_gap_components=len(enclosed),enclosed_gap_pixels=sum(enclosed),
            largest_enclosed_gap_pixels=max(enclosed,default=0),roi_pixels_outside_faceoval=int((union&~face).sum()),
            a68_brow_points_inside=a_brow_inside,native_brow_points_inside=native_inside,
            native_brow_proxy_coverage=float(brow_covered/brow_pixels) if brow_pixels else None,
            prior_visible_risk_tags=risk['image'],occlusion_clearance='UNVERIFIED'))
        if (i+1)%100==0 or i+1==len(names):
            print(f'Raw ROI validation: {i+1}/{len(names)} images; {(i+1)*4} polygons; no priority subtraction',flush=True)
    assert len(roi_rows)==5752 and len(image_rows)==1438 and len(overlap_rows)==8628
    save_csv(OUT/'metrics.csv',roi_rows)
    save_csv(OUT/'image_metrics.csv',image_rows)
    save_csv(OUT/'overlap_metrics.csv',overlap_rows)
    save_csv(OUT/'roi_vertices.csv',vertex_rows)
    reasons=Counter(reason for row in roi_rows for reason in row['geometry_invalid_reasons'].split(';') if reason)
    region_summary={region:dict(roi_count=1438,
        geometry_valid=sum(r['geometry_valid'] for r in roi_rows if r['region']==region),
        continuous_area_px2=stats([r['continuous_area_px2'] for r in roi_rows if r['region']==region]),
        raw_mask_pixels=stats([r['raw_mask_pixels'] for r in roi_rows if r['region']==region]),
        support_valid_centres=stats([r['support_valid_centres'] for r in roi_rows if r['region']==region]),
        predicted_hair_positive_rois=sum(r['predicted_hair_overlap_pixels']>0 for r in roi_rows if r['region']==region)) for region in REGIONS}
    summary=dict(schema_id='C1_ROI_FULL_DATASET_VALIDATION_v0.2.0',status='COMPLETE_GEOMETRY_AUDIT_ANATOMY_PROVISIONAL',
        images_checked=len(image_rows),roi_checked=len(roi_rows),expected_roi_count=5752,
        geometry_valid_rois=sum(r['geometry_valid'] for r in roi_rows),geometry_invalid_rois=sum(not r['geometry_valid'] for r in roi_rows),
        invalid_reasons=dict(reasons),out_of_bounds_rois=sum(r['vertices_outside_image']>0 for r in roi_rows),
        small_roi_review_flags=sum(r['too_small_review'] for r in roi_rows),
        regions=region_summary,overlap_images=sum(r['overlap_unique_pixels']>0 for r in image_rows),
        unique_overlap_pixels=stats([r['overlap_unique_pixels'] for r in image_rows]),
        pairwise_overlap={a+'__'+b:stats([r['overlap_pixels'] for r in overlap_rows if r['region_a']==a and r['region_b']==b]) for a,b in PAIR_KEYS},
        priority_subtraction_applied=False,raw_masks_retained_independently=True,
        unassigned_face_pixels=stats([r['unassigned_face_pixels'] for r in image_rows]),
        enclosed_gap_pixels=stats([r['enclosed_gap_pixels'] for r in image_rows]),
        a68_brow_points_all10_inside_images=sum(r['a68_brow_points_inside']==10 for r in image_rows),
        native_brow_points_all20_inside_images=sum(r['native_brow_points_inside']==20 for r in image_rows),
        native_brow_proxy_full_pixel_coverage_images=sum(r['native_brow_proxy_coverage']==1. for r in image_rows),
        native_brow_proxy_coverage=stats([r['native_brow_proxy_coverage'] for r in image_rows]),
        occlusion_ground_truth_available=False,all_anatomical_status='UNVERIFIED',
        model_hair_proxy_checked_on_all_rois=True,model_hair_proxy_is_ground_truth=False,
        contract_schema_id=contract['schema_id'],contract_file_sha256=digest(OUT/'contract_v0_2.json'),
        contract_content_sha256=contract['content_sha256'],geometry_unchanged_from_proposal=True,
        landmark_archive_sha256=proof['archive_sha256'],model_version=proof['model_version'],
        numpy_version=np.__version__,opencv_version=cv2.__version__,reran_mediapipe=False,
        lbp_extractor_written=False,lbp_applied_to_images=False,c1_c2_vectors_created=False,
        approval_status='PROVISIONAL',full_system_compliance=False)
    write_json(OUT/'summary.json',summary)
    write_json(OUT/'source_proof.json',dict(landmarks=proof,input_hair_manifest_sha256=digest(previous.db.b_v2.DEFAULT_OUTPUT/'manifest.csv'),
        topology_sha256=digest(ROOT/'docs/audits/pre_c_evidence/native_mediapipe_topology.json'),
        face_oval_order=oval,eyebrow_proxy_order=dict(left_viewer=BROW_LEFT,right_viewer=BROW_RIGHT),
        eyebrow_proxy_caveat='Closed two native open chains with straight endpoint bridges; proxy, not hand-labeled eyebrow tissue',
        protected_files=len(baseline),overlap_subtraction_used=False))
    assert 'mediapipe' not in sys.modules
    print(json.dumps({k:summary[k] for k in ['images_checked','roi_checked','geometry_valid_rois','geometry_invalid_rois',
        'small_roi_review_flags','out_of_bounds_rois','overlap_images','native_brow_points_all20_inside_images',
        'native_brow_proxy_full_pixel_coverage_images','native_brow_proxy_coverage','priority_subtraction_applied']},indent=2))


if __name__=='__main__':
    main()
