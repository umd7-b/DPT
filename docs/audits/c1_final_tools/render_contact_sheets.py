"""Representative raw ROI panels and a NON-ACTIVE forehead amendment preview."""
from collections import defaultdict
from pathlib import Path
import copy
import hashlib
import json
import textwrap

import cv2
import numpy as np

import validate_roi_all as audit
from shared.report_v2 import read_csv,read_json,write_json

OUT=audit.OUT
REGIONS=audit.REGIONS
COLORS=dict(forehead_brow=(50,180,250),cheek_left_viewer=(80,205,70),
            cheek_right_viewer=(240,160,50),nose_mouth=(180,60,220))


def text_panel(title,lines,side=384):
    panel=np.full((side+36,side,3),255,np.uint8)
    cv2.putText(panel,title,(8,23),0,.5,(0,0,0),1,cv2.LINE_AA)
    y=60
    for line in lines:
        for part in textwrap.wrap(str(line),53) or ['']:
            cv2.putText(panel,part,(8,y),0,.39,(0,0,0),1,cv2.LINE_AA);y+=22
    return panel


def picture_panel(title,image):
    panel=text_panel(title,[])
    panel[36:]=cv2.resize(image,(384,384),interpolation=cv2.INTER_NEAREST)
    return panel


def select_cases(rows,image_rows):
    selected=defaultdict(list)
    for key,label in [
        ('cfd_final_00001','normal_CFD'),('cfd_final_00069','CFD_expression'),('hf_merged_00001','normal_HF'),
        ('hf_merged_00561','forehead_hair_and_secondary_face'),('hf_merged_00694','glasses_and_cloth'),
        ('hf_merged_00722','hand_occlusion'),('hf_merged_00209','head_covering'),
        ('hf_merged_00333','secondary_faces')]:
        selected[key].append(label)
    for region in REGIONS:
        subset=[r for r in rows if r['region']==region]
        for field,label in [('raw_mask_pixels','minimum_observed_raw_pixels'),('support_valid_centres','minimum_observed_support')]:
            row=min(subset,key=lambda r:(int(r[field]),r['image_id']))
            selected[row['image_id']].append(region+':'+label)
    extremes=[('overlap_unique_pixels',True,'maximum_overlap'),('unassigned_face_pixels',True,'maximum_unassigned_face'),
              ('native_brow_proxy_coverage',False,'minimum_native_brow_proxy_coverage')]
    for field,reverse,label in extremes:
        row=sorted(image_rows,key=lambda r:((-1 if reverse else 1)*float(r[field]),r['image_id']))[0]
        selected[row['image_id']].append(label)
    forehead=[r for r in rows if r['region']=='forehead_brow']
    row=max(forehead,key=lambda r:(float(r['predicted_hair_overlap_fraction']),r['image_id']))
    selected[row['image_id']].append('maximum_predicted_forehead_hair_fraction_NOT_GT')
    region_map=defaultdict(dict)
    for r in rows:region_map[r['image_id']][r['region']]=int(r['raw_mask_pixels'])
    ratio=lambda key:max(region_map[key]['cheek_left_viewer']/max(1,region_map[key]['cheek_right_viewer']),
                         region_map[key]['cheek_right_viewer']/max(1,region_map[key]['cheek_left_viewer']))
    key=sorted(region_map,key=lambda key:(-ratio(key),key))[0]
    selected[key].append('maximum_left_right_area_asymmetry_proxy')
    actual_bad=sorted({r['image_id'] for r in rows if r['geometry_valid']=='False' or r['too_small_review']=='True' or int(r['vertices_outside_image'])>0})
    for key in actual_bad[:12]:selected[key].append('actual_geometry_or_size_warning')
    return dict(sorted(selected.items()))


def render_case(identity,name,p,image,contract,metrics,imetrics,case_labels,indices):
    groups,_=audit.previous.source_groups()
    polygons=audit.previous.polygon_points(p,contract,groups)
    masks={k:audit.raw_mask(v) for k,v in polygons.items()}
    for key in REGIONS:
        assert int(masks[key].sum())==int(metrics[key]['raw_mask_pixels'])
        assert hashlib.sha256(masks[key].tobytes()).hexdigest()==metrics[key]['raw_mask_sha256']
    folder=OUT/'contact_sheets'/identity
    folder.mkdir(parents=True,exist_ok=True)
    for key in REGIONS:
        cv2.imwrite(str(folder/(key+'_raw_mask.png')),masks[key]*255)
    landmark=image.copy()
    for j,xy in enumerate(p[indices]):
        x,y=np.rint(xy).astype(int)
        cv2.circle(landmark,(x,y),1,(0,255,255),-1)
        cv2.putText(landmark,str(j),(x+1,y-1),0,.22,(0,0,0),1,cv2.LINE_AA)
    count=np.sum(np.stack(list(masks.values())),axis=0)
    union=count>0
    raw=image.copy()
    color=np.zeros(image.shape,float)
    for key in REGIONS:color+=masks[key][...,None]*np.array(COLORS[key])
    avg=np.divide(color,count[...,None],out=np.zeros_like(color),where=count[...,None]>0)
    raw[union]=np.rint(.7*image[union]+.3*avg[union]).astype(np.uint8)
    for key,v in polygons.items():cv2.polylines(raw,[np.rint(v).astype(np.int32)],True,COLORS[key],1,cv2.LINE_AA)
    overlap=image.copy(); overlap[count>=2]=(0,0,255)
    native=read_json(audit.ROOT/'docs/audits/pre_c_evidence/native_mediapipe_topology.json')
    face=audit.raw_mask(p[audit.face_oval_order(native)]).astype(bool)
    gap=image.copy();gap[face & ~union]=(180,40,180)
    mask_panels={k:picture_panel(k+' RAW',cv2.cvtColor(masks[k]*255,cv2.COLOR_GRAY2BGR)) for k in REGIONS}
    geo=sum(metrics[k]['geometry_valid']=='True' for k in REGIONS)
    lines=[name,f'GEOMETRY VALID {geo}/4; ANATOMY UNVERIFIED',
        *[f"{k}: {metrics[k]['raw_mask_pixels']} px / support {metrics[k]['support_valid_centres']}" for k in REGIONS],
        f"Shared pixels: {imetrics['overlap_unique_pixels']}; no priority subtraction",
        f"Unassigned face: {imetrics['unassigned_face_pixels']} (includes eyes/chin)",
        f"Native brow proxy coverage: {100*float(imetrics['native_brow_proxy_coverage']):.2f}%",
        'Hair/hand/cloth/glasses are NOT automatically cleared.',*case_labels]
    panels=[picture_panel('Original full frame',image),picture_panel('A68 indices (mapping unchanged)',landmark),
        picture_panel('Four ORIGINAL raw polygons',raw),mask_panels['forehead_brow'],mask_panels['cheek_left_viewer'],
        mask_panels['cheek_right_viewer'],mask_panels['nose_mouth'],picture_panel('Overlap pixels RED',overlap),
        picture_panel('Unassigned within native face proxy',gap),text_panel('Measurements / review labels',lines)]
    canvas=np.vstack([np.hstack(panels[:5]),np.hstack(panels[5:])])
    path=folder/'contact.png'
    assert cv2.imwrite(str(path),canvas)
    return path,masks,polygons


def amendment(contract):
    candidate=copy.deepcopy(contract)
    lower=[276,283,282,295,285,55,65,52,53,46]
    candidate['polygons']['forehead_brow']=[dict(ref='MP478_AUX',index=i,mediapipe_index=i,
        offset_u_ipd=0.,offset_v_ipd=0.) for i in contract['auxiliary_upper_face_oval']]+[
        dict(ref='MP478_AUX_PROPOSED_LOWER_BROW',index=i,mediapipe_index=i,offset_u_ipd=0.,offset_v_ipd=.02) for i in lower]
    return candidate,dict(schema_id='C1_FOREHEAD_AMENDMENT_PROPOSAL_v0.3.0',status='PROPOSED_NOT_ACTIVE',
        base_contract_id=contract['schema_id'],reason='Validate lower-eyebrow coverage without changing any A mapping.',
        polygon=candidate['polygons']['forehead_brow'],margin_ipd=.02,
        anatomical_status='UNVERIFIED; lower native contour is a proxy, not hair/tissue ground truth',
        active_contract_changed=False,decision_not_based_on_retrieval=True)


def main():
    if not (OUT/'summary.json').exists():raise FileNotFoundError('Run full validation first')
    if (OUT/'case_selection.json').exists():raise FileExistsError('Contact-sheet delivery already exists')
    rows=read_csv(OUT/'metrics.csv');imrows=read_csv(OUT/'image_metrics.csv')
    cases=select_cases(rows,imrows)
    by_image=defaultdict(dict)
    for r in rows:by_image[r['image_id']][r['region']]=r
    imap={r['image_id']:r for r in imrows}
    names,points,images,_,_=audit.previous.load_archive()
    positions={Path(name).stem:i for i,name in enumerate(names)}
    contract=read_json(OUT/'contract_v0_2.json')
    groups,indices=audit.previous.source_groups()
    candidate,amendment_spec=amendment(contract)
    native=read_json(audit.ROOT/'docs/audits/pre_c_evidence/native_mediapipe_topology.json')
    brow_nodes={i for key in ['FACE_LANDMARKS_LEFT_EYEBROW','FACE_LANDMARKS_RIGHT_EYEBROW'] for edge in native['edges'][key] for i in edge}
    assert all(ref['mediapipe_index'] in brow_nodes for ref in candidate['polygons']['forehead_brow'][15:])
    write_json(OUT/'forehead_amendment_proposal_v0_3.json',amendment_spec)
    comparisons=[];files=[]
    for identity,labels in cases.items():
        i=positions[identity];name=names[i];p=points[i]
        image=cv2.imread(images[name]['image_path'])
        path,masks,polygons=render_case(identity,name,p,image,contract,by_image[identity],imap[identity],labels,indices)
        files.append(dict(image_id=identity,reasons=labels,contact_sheet=str(path.relative_to(audit.ROOT))))
        before=polygons['forehead_brow'];after=audit.previous.polygon_points(p,candidate,groups)['forehead_brow']
        oldmask=masks['forehead_brow'];newmask=audit.raw_mask(after)
        proxy=np.maximum(audit.raw_mask(p[audit.BROW_LEFT]),audit.raw_mask(p[audit.BROW_RIGHT])).astype(bool)
        proxy_count=int(proxy.sum())
        comparison=image.copy()
        cv2.polylines(comparison,[np.rint(before).astype(np.int32)],True,(0,160,255),1)
        cv2.polylines(comparison,[np.rint(after).astype(np.int32)],True,(0,200,0),1)
        added=(newmask!=0)&(oldmask==0)
        overlay=image.copy();overlay[added]=(0,220,0)
        before_fraction=float((proxy & (oldmask!=0)).sum()/proxy_count)
        after_fraction=float((proxy & (newmask!=0)).sum()/proxy_count)
        valid=not audit.previous.self_intersects(after) and abs(cv2.contourArea(after.astype(np.float32)))>1e-6
        out=OUT/'proposal_comparisons'/f'{identity}_forehead.png';out.parent.mkdir(exist_ok=True)
        canvas=np.hstack([picture_panel('ACTIVE orange / PROPOSED green',comparison),
            picture_panel('Added pixels GREEN (not activated)',overlay),text_panel('Forehead amendment proposal',[
            name,'PROPOSED ONLY; anatomy UNVERIFIED',f'Native eyebrow proxy before: {before_fraction:.6f}',
            f'Native eyebrow proxy after: {after_fraction:.6f}',f'Candidate simple geometry: {valid}',
            'Original contract and all A indices unchanged.',
            'Not a fix for cloth/hair/hand/glasses.', 'Lower native brow chain +0.02 IPD; margin is an implementation proposal.'])])
        assert cv2.imwrite(str(out),canvas)
        comparisons.append(dict(image_id=identity,before_brow_proxy_coverage=before_fraction,
            proposed_brow_proxy_coverage=after_fraction,candidate_geometry_valid=valid,
            active_geometry_changed=False,comparison_image=str(out.relative_to(audit.ROOT))))
    write_json(OUT/'case_selection.json',dict(strategy='Required observed categories + deterministic full-dataset extrema, never retrieval results',
        cases=files,actual_bad_geometry_or_small_roi_count=sum(r['geometry_valid']=='False' or r['too_small_review']=='True' for r in rows),
        no_synthetic_bad_cases_created=True))
    write_json(OUT/'forehead_amendment_comparisons.json',comparisons)
    # Fixed 50 CFD / 50 HF technical-trial manifest; includes mandatory/extreme cases.
    selected=set(cases)
    for source in ['cfd','hf']:
        pool=[r['image_id'] for r in imrows if r['source'].lower()==source]
        already={key for key in selected if imap[key]['source'].lower()==source}
        assert len(already)<=50
        rest=sorted(set(pool)-already,key=lambda key:(hashlib.sha256(('C1_trial100_v0.2:'+key).encode()).hexdigest(),key))
        selected.update(rest[:50-len(already)])
    assert len(selected)==100
    trial=[]
    for key in sorted(selected):
        ready=all(by_image[key][region]['geometry_valid']=='True' and int(by_image[key][region]['support_valid_centres'])>=64 for region in REGIONS)
        trial.append(dict(image_id=key,source=imap[key]['source'],technical_roi_support_ready=ready,
            expected_geometry_path='processable' if ready else 'must_return_missing_C1',anatomy='UNVERIFIED',
            included_for=cases.get(key,['seeded_source_balanced_fill'])))
    write_json(OUT/'trial100_manifest.json',dict(schema_id='C1_TECHNICAL_TRIAL100_PLAN_v0.2.0',
        count=100,source_counts=dict(cfd=50,hf=50),trial_executed=False,extractor_implemented=False,
        purpose='Future algorithm/serialization smoke test only; not anatomical or retrieval-quality certification',
        contract_file_sha256=audit.digest(OUT/'contract_v0_2.json'),images=trial))
    print(json.dumps(dict(contact_sheet_cases=len(cases),proposal_comparisons=len(comparisons),
        trial_manifest_count=100,trial_executed=False,priority_subtraction_applied=False),indent=2))


if __name__=='__main__':
    main()
