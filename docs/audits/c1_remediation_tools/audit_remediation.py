"""Geometry/anatomy evidence only. Never invokes LBP/HOG, fitting or ranking.

Uses authenticated saved landmarks and the frozen audit's raster/support rules.
Writes exclusively to a new namespace, leaving the active v0.2 contract alone.
"""
from pathlib import Path
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import itertools
import json
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docs/audits/c1_final_tools'))
sys.path.insert(0, str(ROOT))
import validate_roi_all as frozen
from verify_full_validation import segment_intersections

OUT = ROOT / 'outputs/C1_lbp/roi_remediation_v0_4'
OLD = ROOT / 'outputs/C1_lbp/roi_validation'
REGIONS = frozen.REGIONS
NEGATIVE = ['hf_merged_00069', 'hf_merged_00198', 'hf_merged_00267', 'hf_merged_00463']
LOWER = [276, 283, 282, 295, 285, 55, 65, 52, 53, 46]
ROI_PIN = '61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c'
SPEC_PIN = '7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False,
                  default=lambda obj: obj.tolist() if isinstance(obj, np.ndarray) else obj.item())
        stream.write('\n')


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, rows):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def check_sources():
    baseline = read_json(OUT / 'baseline_before.json')
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or digest(p) != h]
    if changed:
        raise ValueError('Protected artifacts changed: ' + repr(changed[:10]))
    for filename, pin in [('contract_v0_2.json', ROI_PIN), ('lbp_implementation_spec.json', SPEC_PIN)]:
        value = read_json(OLD / filename)
        stored = value.pop('content_sha256')
        if stored != pin or canonical(value) != pin:
            raise ValueError('Pinned content mismatch: ' + filename)
    if digest(r'C:\Users\USER\Downloads\csdldpt.pdf') != '8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80':
        raise ValueError('Authoritative PDF changed')
    return baseline


def variants(base, proposal):
    comparison = copy.deepcopy(base)
    comparison['polygons']['forehead_brow'] = copy.deepcopy(proposal['polygon'])
    candidate = copy.deepcopy(base)
    # No search/tuning of a margin. Zero offset follows the unshifted native contour.
    candidate['polygons']['forehead_brow'] = copy.deepcopy(proposal['polygon'])
    for item in candidate['polygons']['forehead_brow'][15:]:
        item['offset_v_ipd'] = 0.
    for key in ['content_sha256', 'geometry_sha256', 'source_proposal_id', 'source_proposal_sha256',
                'modifications_proposed_but_not_active', 'extractor_implemented', 'c1_c2_vectors_created']:
        candidate.pop(key, None)
    candidate.update(schema_id='C1_ROI_ANATOMICAL_CANDIDATE_v0.4.0', version='0.4.0',
        status='PROVISIONAL', anatomy_status='ANATOMY_PROVISIONAL', active=False,
        source_contract=dict(schema_id=base['schema_id'], content_sha256=base['content_sha256'],
                             file_sha256=digest(OLD / 'contract_v0_2.json')),
        source_forehead_proposal=dict(schema_id=proposal['schema_id'], file_sha256=digest(OLD / 'forehead_amendment_proposal_v0_3.json')),
        boundary_rationale=dict(upper='Retain all15 upper FACE_OVAL nodes and their order; not a hairline annotation',
            lower='Replace the five-point upper brow per side with the native lower brow contours; retain their anatomical order',
            zero_offset='Remove unsupported +0.02D downshift from v0.3. At HF00198 the sloped temporal face boundary makes a global downward shift cross it.',
            no_arbitrary_vertex_deletion=True, no_reorder_or_hull=True, offset_search_performed=False,
            limitations='Sparse native contours are model proxies; neither perfect coverage nor a simple polygon is anatomical ground truth'),
        changes=dict(forehead_lower_chain=LOWER, forehead_lower_offset_v_ipd=0.,
                     unchanged_regions=REGIONS[1:], unchanged_A_mapping=True,
                     no_active_extractor_or_trial_updates=True),
        outside_rule='Only image clipping at raster evaluation, not face-oval clipping or vertex repair',
        overlapping_regions='Raw independent membership retained; no ownership subtraction',
        source_hashes=dict(landmarks=digest(frozen.previous.ARCHIVE), native_topology=digest(ROOT / 'docs/audits/pre_c_evidence/native_mediapipe_topology.json'),
                           report=digest(r'C:\Users\USER\Downloads\csdldpt.pdf')),
        decision_basis='HF00198 edge/offset diagnosis and lower-brow membership; chosen before full census, never retrieval scores',
        geometric_validation='See separate census and verification; this candidate file does not grant anatomical acceptance')
    candidate['geometry_sha256'] = canonical(candidate['polygons'])
    candidate['content_sha256'] = canonical(candidate)
    return {'v0_2': base, 'v0_3': comparison, 'candidate_v0_4': candidate}


def crossing_details(vertices, definition):
    details = segment_intersections(vertices)
    for detail in details:
        detail['endpoints'] = {key: [dict(vertex_order=i, xy=vertices[i].tolist(), **definition[i]) for i in detail[key]]
                               for key in ('edge_a', 'edge_b')}
        i, j = detail['edge_a'][0], detail['edge_b'][0]
        # Independent linear solve verifies the determinant intersection.
        matrix = np.column_stack((vertices[(i + 1) % len(vertices)] - vertices[i],
                                  -(vertices[(j + 1) % len(vertices)] - vertices[j])))
        parameters = np.linalg.solve(matrix, vertices[j] - vertices[i])
        xy = vertices[i] + parameters[0] * matrix[:, 0]
        assert np.max(np.abs(xy - detail['intersection_xy'])) < 1e-10
        detail['independent_linear_solve_residual'] = float(np.max(np.abs(xy - detail['intersection_xy'])))
        detail['involves_polygon_closure_edge'] = (len(vertices) - 1 in [i, j])
    return details


def diagnose(names, points, groups, contracts, images):
    positions = {Path(name).stem: i for i, name in enumerate(names)}
    records = []
    for identity in NEGATIVE:
        p = points[positions[identity]]
        item = dict(image_id=identity, archive_row=positions[identity], image_hash=images[names[positions[identity]]]['image_hash'],
                    landmark_row_sha256=hashlib.sha256(p.tobytes()).hexdigest(), variants={})
        left, right = p[groups['LEFT_EYE']].mean(axis=0).astype(float), p[groups['RIGHT_EYE']].mean(axis=0).astype(float)
        distance = float(np.linalg.norm(right - left)); u = (right - left) / distance
        v = np.array([-u[1], u[0]])
        item['frame'] = dict(left=left.tolist(), right=right.tolist(), D=distance, u=u.tolist(), v=v.tolist())
        for tag, contract in contracts.items():
            vertices = frozen.previous.polygon_points(p, contract, groups)['forehead_brow']
            item['variants'][tag] = dict(vertices=vertices.tolist(), crossings=crossing_details(vertices, contract['polygons']['forehead_brow']),
                self_intersection=frozen.previous.self_intersects(vertices))
        # Explicit counterfactual separates source-contour/endpoint choice from offset.
        original_no_offset = copy.deepcopy(contracts['v0_2'])
        for vertex in original_no_offset['polygons']['forehead_brow'][15:]:
            vertex['offset_v_ipd'] = 0.
        xy = frozen.previous.polygon_points(p, original_no_offset, groups)['forehead_brow']
        item['diagnostic_counterfactual_A68_upper_brow_no_offset'] = crossing_details(xy, original_no_offset['polygons']['forehead_brow'])
        # Signed side test at the native left lower-brow endpoint versus first upper-oval edge.
        native = item['variants']['candidate_v0_4']['vertices']
        shifted = item['variants']['v0_3']['vertices']
        a, b = np.asarray(native[0]), np.asarray(native[1])
        signed = lambda q: float((b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]))
        item['temporal_offset_side_test'] = dict(edge=[0, 1], edge_mp=[127, 162],
            unshifted_MP46_xy=native[24], shifted_MP46_xy=shifted[24],
            signed_cross_unshifted=signed(native[24]), signed_cross_shifted=signed(shifted[24]),
            displacement_xy=(.02 * distance * v).tolist(),
            interpretation='Signs test the line side, not tissue boundaries; relevant proper segment crossing is separately verified')
        records.append(item)
    return records


def endpoint_evidence(contracts, native):
    edge_membership = {name: {n for edge in edges for n in edge} for name, edges in native['edges'].items()}
    indices = contracts['v0_2']['indices68_unchanged']
    inverse = {mp: i for i, mp in enumerate(indices)}
    rows = []
    for variant, contract in contracts.items():
        for region in REGIONS:
            for j, item in enumerate(contract['polygons'][region]):
                mp = item['mediapipe_index']
                memberships = [name for name, nodes in edge_membership.items() if mp in nodes]
                rows.append(dict(variant=variant, region=region, vertex_order=j, ref=item['ref'],
                    index68=inverse.get(mp), mediapipe_index=mp, offset_u_ipd=item['offset_u_ipd'],
                    offset_v_ipd=item['offset_v_ipd'], contour_memberships=';'.join(memberships),
                    PDF_specifies='Four region names and landmarks based partition; no MP endpoint IDs/margins',
                    endpoint_status='UNVERIFIED_CANONICAL_ENDPOINT',
                    implementation_status='IMPLEMENTATION_DETAIL_PROVISIONAL',
                    next_vertex_order=(j + 1) % len(contract['polygons'][region])))
    return rows


def main():
    if (OUT / 'summary.json').exists() or (OUT / 'candidate_contract_v0_4.json').exists():
        raise FileExistsError('Remediation evidence already started/completed; no overwrite')
    baseline = check_sources()
    names, points, images, measurements, provenance = frozen.previous.load_archive()
    groups, indices = frozen.previous.source_groups()
    base = read_json(OLD / 'contract_v0_2.json')
    proposal = read_json(OLD / 'forehead_amendment_proposal_v0_3.json')
    native = read_json(ROOT / 'docs/audits/pre_c_evidence/native_mediapipe_topology.json')
    contracts = variants(base, proposal)
    # Freeze the geometrical choice before reading any candidate full-corpus metric.
    write_json(OUT / 'candidate_contract_v0_4.json', contracts['candidate_v0_4'])
    write_json(OUT / 'decision_before_census.json', dict(candidate_sha256=digest(OUT / 'candidate_contract_v0_4.json'),
        reason=contracts['candidate_v0_4']['boundary_rationale'], candidate_parameters_chosen_before_census=True,
        tunable_searches=0, retrieval_comparisons=0, variant_evaluation_plan=['v0_2', 'v0_3', 'candidate_v0_4']))
    anomalies = diagnose(names, points, groups, contracts, images)
    write_json(OUT / 'four_cases_intersections.json', anomalies)
    save_csv(OUT / 'endpoint_contract_review.csv', endpoint_evidence(contracts, native))
    write_json(OUT / 'source_proof.json', dict(provenance=provenance, saved_package_topology_sha256=digest(ROOT / 'docs/audits/pre_c_evidence/native_mediapipe_topology.json'),
        pixel_geometry_frame='pixel_xy; x right y down; viewer/code left/right; mean6 float32 eyes then float64',
        baseline_file_count=len(baseline), source_files={f: digest(OLD / f) for f in ['contract_v0_2.json', 'forehead_amendment_proposal_v0_3.json', 'lbp_implementation_spec.json']},
        scope='Geometry audit only; no LBP/HOG/codes/histograms/features, no detector or DB writes'))
    old_metrics = {(r['image_id'], r['region']): r for r in read_csv(OLD / 'metrics.csv')}
    b_manifest = {r['image_id']: r for r in read_csv(frozen.previous.db.b_v2.DEFAULT_OUTPUT / 'manifest.csv')}
    all_rows, overlap_rows, image_rows, vertex_rows = [], [], [], []
    for count, (name, p) in enumerate(zip(names, points), 1):
        image = images[name]; identity = image['image_id']
        b = b_manifest[identity]
        if digest(b['hair_mask_path']) != b['hair_mask_sha256']:
            raise ValueError('Frozen hair mask changed')
        hair = cv2.imread(b['hair_mask_path'], cv2.IMREAD_GRAYSCALE) != 0
        proxy_masks = [frozen.raw_mask(p[chain]) for chain in (frozen.BROW_LEFT, frozen.BROW_RIGHT)]
        proxy = np.maximum(*proxy_masks).astype(bool)
        native_brow_nodes = sorted(set(frozen.BROW_LEFT + frozen.BROW_RIGHT))
        old_masks = None
        for variant, contract in contracts.items():
            polygons = frozen.previous.polygon_points(p, contract, groups)
            masks = {r: frozen.raw_mask(polygons[r]) if variant == 'v0_2' or r == 'forehead_brow'
                     else old_masks[r].copy() for r in REGIONS}
            if variant == 'v0_2': old_masks = masks
            for region in REGIONS:
                v, mask = polygons[region], masks[region]
                invalid = frozen.previous.self_intersects(v)
                finite = bool(np.isfinite(v).all())
                area = abs(float(cv2.contourArea(v.astype(np.float32))))
                eligible = frozen.support_centres(mask)
                pixels, support = int(mask.sum()), int(eligible.sum())
                valid = finite and not invalid and area >= 1e-6 and pixels > 0
                error = 'self_intersection' if invalid else ('invalid_area_or_empty' if not valid else '')
                proxy_covered = int((proxy & (mask != 0)).sum())
                row = dict(variant=variant, image_id=identity, image_name=name, source=image['source'], region=region,
                    vertex_count=len(v), finite_coordinates=finite, self_intersection=invalid,
                    geometry_valid=valid, geometry_invalid_reason=error, continuous_area_px2=area,
                    raw_mask_pixels=pixels, eligible_centres=support, insufficient_support=support < 64,
                    vertices_outside_image=int(np.count_nonzero((v[:, 0] < 0) | (v[:, 0] >= 256) | (v[:, 1] < 0) | (v[:, 1] >= 256))),
                    raw_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
                    pixels_added_vs_v0_2=int(((mask != 0) & (old_masks[region] == 0)).sum()),
                    pixels_removed_vs_v0_2=int(((mask == 0) & (old_masks[region] != 0)).sum()),
                    predicted_hair_overlap_pixels=int((hair & (mask != 0)).sum()),
                    predicted_hair_overlap_fraction=float((hair & (mask != 0)).sum() / pixels) if pixels else None,
                    hair_evidence='SAVED_B_MASK_MODEL_PROXY_NOT_GT',
                    brow_proxy_pixels=int(proxy.sum()) if region == 'forehead_brow' else None,
                    brow_proxy_covered_pixels=proxy_covered if region == 'forehead_brow' else None,
                    brow_proxy_coverage=float(proxy_covered / proxy.sum()) if region == 'forehead_brow' else None,
                    brow_left_coverage=float(((proxy_masks[0] != 0) & (mask != 0)).sum() / proxy_masks[0].sum()) if region == 'forehead_brow' else None,
                    brow_right_coverage=float(((proxy_masks[1] != 0) & (mask != 0)).sum() / proxy_masks[1].sum()) if region == 'forehead_brow' else None,
                    anatomy_status='ANATOMY_PROVISIONAL', occlusion_clearance='UNVERIFIED',
                    known_image_risk=frozen.KNOWN.get(identity, {}).get('image', 'UNVERIFIED'))
                if variant == 'v0_2':
                    old = old_metrics[(identity, region)]
                    assert row['raw_mask_sha256'] == old['raw_mask_sha256']
                    assert pixels == int(old['raw_mask_pixels']) and support == int(old['support_valid_centres'])
                    assert valid == (old['geometry_valid'] == 'True')
                all_rows.append(row)
                if variant != 'v0_2':
                    for j, (point, definition) in enumerate(zip(v, contract['polygons'][region])):
                        vertex_rows.append(dict(variant=variant, image_id=identity, region=region, vertex_order=j,
                            ref=definition['ref'], index68=indices.index(definition['mediapipe_index']) if definition['mediapipe_index'] in indices else None,
                            mediapipe_index=definition['mediapipe_index'], offset_u_ipd=definition['offset_u_ipd'],
                            offset_v_ipd=definition['offset_v_ipd'], x=float(point[0]), y=float(point[1])))
            membership = np.sum(np.stack(list(masks.values())), axis=0)
            for a, b in itertools.combinations(REGIONS, 2):
                overlap_rows.append(dict(variant=variant, image_id=identity, region_a=a, region_b=b,
                    overlap_pixels=int(((masks[a] != 0) & (masks[b] != 0)).sum()), ownership_subtraction=False))
            brow = masks['forehead_brow']
            image_rows.append(dict(variant=variant, image_id=identity, source=image['source'],
                changed_regions=';'.join(r for r in REGIONS if not np.array_equal(masks[r], old_masks[r])),
                overlap_unique_pixels=int((membership >= 2).sum()), raw_union_pixels=int((membership > 0).sum()),
                max_memberships=int(membership.max()), anatomy_status='ANATOMY_PROVISIONAL',
                native_brow_nodes_covered=sum(cv2.pointPolygonTest(polygons['forehead_brow'].astype(np.float32),
                                              tuple(map(float, p[j])), False) >= 0 for j in native_brow_nodes),
                known_image_risk=frozen.KNOWN.get(identity, {}).get('image', 'UNVERIFIED')))
        if count % 100 == 0 or count == len(names):
            print(f'Audited {count}/1438 images, all4 ROIs x3 variants; no feature extraction', flush=True)
    save_csv(OUT / 'roi_metrics.csv', all_rows)
    save_csv(OUT / 'image_metrics.csv', image_rows)
    save_csv(OUT / 'overlap_metrics.csv', overlap_rows)
    save_csv(OUT / 'candidate_vertices.csv', vertex_rows)
    summaries = {}
    for variant in contracts:
        rows = [r for r in all_rows if r['variant'] == variant]
        forehead = [r for r in rows if r['region'] == 'forehead_brow']
        image_metrics = [r for r in image_rows if r['variant'] == variant]
        coverage = np.array([r['brow_proxy_coverage'] for r in forehead])
        summaries[variant] = dict(roi_count=len(rows), valid_geometry=sum(r['geometry_valid'] for r in rows),
            self_intersections=sum(r['self_intersection'] for r in rows), insufficient_support=sum(r['insufficient_support'] for r in rows),
            vertices_outside_image=sum(r['vertices_outside_image'] for r in rows),
            invalid_images=sorted({r['image_id'] for r in rows if not r['geometry_valid']}),
            changed_images=sum(bool(r['changed_regions']) for r in image_metrics),
            brow_proxy_coverage_min=float(coverage.min()), brow_proxy_coverage_median=float(np.median(coverage)),
            brow_proxy_coverage_max=float(coverage.max()), full_proxy_coverage_images=sum(coverage == 1.),
            overlap_unique_min=min(r['overlap_unique_pixels'] for r in image_metrics),
            overlap_unique_max=max(r['overlap_unique_pixels'] for r in image_metrics),
            max_predicted_forehead_hair_fraction=max(r['predicted_hair_overlap_fraction'] for r in forehead),
            anatomical_ground_truth_images=0, anatomy_status='ANATOMY_PROVISIONAL')
    write_json(OUT / 'summary.json', dict(schema_id='C1_ROI_REMEDIATION_CENSUS_v0.4.0', image_count=len(names),
        variants=summaries, candidate_content_sha256=contracts['candidate_v0_4']['content_sha256'],
        geometry_status='GEOMETRY_VALIDATED' if summaries['candidate_v0_4']['valid_geometry'] == 5752 else 'GEOMETRY_ISSUES_REMAIN',
        anatomy_status='ANATOMY_PROVISIONAL', candidate_activated=False, candidate_parameters_retuned_after_census=False,
        full_corpus_review_is_geometrical_not_manual_anatomical=True, LBPHOG_calls=0, C1C2_vectors_created=0, retrieval_comparisons=0))
    print(json.dumps(summaries, ensure_ascii=False, indent=2, default=lambda obj: obj.item()), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--check-completed']:
        check_sources()
        summary = read_json(OUT / 'summary.json')
        assert len(read_csv(OUT / 'roi_metrics.csv')) == 17256
        assert len(read_csv(OUT / 'overlap_metrics.csv')) == 25884
        assert len(read_csv(OUT / 'candidate_vertices.csv')) == 175436
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    else:
        main()
