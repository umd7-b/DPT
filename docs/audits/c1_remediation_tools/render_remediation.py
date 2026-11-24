"""Diagnostic displays only; never changes source images or accepted outputs."""
from collections import defaultdict
import json
import textwrap

import cv2
import numpy as np

import audit_remediation as audit

COLORS = [(0, 170, 250), (50, 190, 80), (240, 170, 30), (210, 60, 170)]
SIDE = 512


def caption(image, title, footer='ANATOMY_PROVISIONAL; proposal not active'):
    panel = np.full((SIDE + 65, SIDE, 3), 250, np.uint8)
    panel[35:35 + SIDE] = cv2.resize(image, (SIDE, SIDE), interpolation=cv2.INTER_NEAREST)
    cv2.putText(panel, title, (8, 24), 0, .54, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(panel, footer, (8, SIDE + 56), 0, .37, (20, 20, 20), 1, cv2.LINE_AA)
    return panel


def drawn(image, p, polygons, brow_proxy=True, crossing=False, labels=False):
    result = cv2.resize(image, (SIDE, SIDE), interpolation=cv2.INTER_NEAREST)
    if brow_proxy:
        for chain in (audit.frozen.BROW_LEFT, audit.frozen.BROW_RIGHT):
            cv2.polylines(result, [np.rint(p[chain] * 2).astype(np.int32)], True, (220, 80, 220), 1, cv2.LINE_AA)
    for j, region in enumerate(audit.REGIONS):
        vertices = polygons[region]
        xy = np.rint(vertices * 2).astype(np.int32)
        cv2.polylines(result, [xy], True, COLORS[j], 2, cv2.LINE_AA)
        if labels and region == 'forehead_brow':
            for order, (x, y) in enumerate(xy):
                cv2.circle(result, (int(x), int(y)), 2, (0, 0, 0), -1)
                cv2.putText(result, str(order), (int(x) + 2, int(y) - 2), 0, .36, (0, 0, 0), 1, cv2.LINE_AA)
        if crossing:
            for entry in audit.segment_intersections(vertices):
                for key in ('edge_a', 'edge_b'):
                    a, b = entry[key]
                    cv2.line(result, tuple(xy[a]), tuple(xy[b]), (0, 0, 255), 3, cv2.LINE_AA)
                x, y = np.rint(np.array(entry['intersection_xy']) * 2).astype(int)
                cv2.drawMarker(result, (x, y), (255, 255, 255), cv2.MARKER_TILTED_CROSS, 14, 2)
    return result


def wrap_panel(title, lines):
    result = np.full((SIDE + 65, SIDE, 3), 250, np.uint8)
    cv2.putText(result, title, (12, 26), 0, .6, (0, 0, 0), 1, cv2.LINE_AA)
    y = 55
    for line in lines:
        for part in textwrap.wrap(line, 67):
            cv2.putText(result, part, (12, y), 0, .4, (20, 20, 20), 1, cv2.LINE_AA)
            y += 20
        y += 6
    return result


def panel_large(image, title):
    result = np.full((SIDE + 65, SIDE, 3), 250, np.uint8)
    result[35:SIDE + 35] = image
    cv2.putText(result, title, (8, 24), 0, .54, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(result, 'ANATOMY_PROVISIONAL; pixel boundaries are model proxies', (8, SIDE + 56), 0, .34, (20, 20, 20), 1, cv2.LINE_AA)
    return result


def main():
    out = audit.OUT
    if (out / 'contact_sheets').exists():
        raise FileExistsError('Contact-sheet output exists')
    summary = audit.read_json(out / 'summary.json')
    rows = audit.read_csv(out / 'roi_metrics.csv')
    by_key = {(r['variant'], r['image_id'], r['region']): r for r in rows}
    selection = defaultdict(list)
    for identity in audit.NEGATIVE: selection[identity].append('required_self_intersection_case')
    for identity in ['cfd_final_00001', 'cfd_final_00069', 'hf_merged_00001']:
        selection[identity].append('fixed_CFD_HF_anatomy_display')
    for identity in audit.frozen.KNOWN: selection[identity].append('known_dataset_or_occlusion_review_case')
    candidates = [r for r in rows if r['variant'] == 'candidate_v0_4' and r['region'] == 'forehead_brow']
    for field, largest, label in [('brow_proxy_coverage', False, 'minimum_candidate_brow_proxy_coverage'),
                                   ('predicted_hair_overlap_fraction', True, 'maximum_saved_hair_mask_fraction_NOT_GT'),
                                   ('raw_mask_pixels', False, 'minimum_candidate_forehead_pixels'),
                                   ('pixels_added_vs_v0_2', True, 'maximum_added_forehead_pixels')]:
        extreme = sorted(candidates, key=lambda r: ((-1 if largest else 1) * float(r[field]), r['image_id']))[0]
        selection[extreme['image_id']].append(label)
    for r in rows:
        if r['variant'] == 'candidate_v0_4' and r['geometry_valid'] != 'True':
            selection[r['image_id']].append('remaining_candidate_invalid_geometry')
    names, points, images, _, _ = audit.frozen.previous.load_archive()
    positions = {audit.Path(name).stem: i for i, name in enumerate(names)}
    groups, indices = audit.frozen.previous.source_groups()
    base = audit.read_json(audit.OLD / 'contract_v0_2.json')
    v03 = json.loads(json.dumps(base)); v03['polygons']['forehead_brow'] = audit.read_json(audit.OLD / 'forehead_amendment_proposal_v0_3.json')['polygon']
    contracts = dict(v0_2=base, v0_3=v03, candidate_v0_4=audit.read_json(out / 'candidate_contract_v0_4.json'))
    (out / 'contact_sheets').mkdir()
    records, mini_panels = [], []
    for identity, reasons in sorted(selection.items()):
        i = positions[identity]; p = points[i]; name = names[i]
        source = images[name]; image = cv2.imread(source['image_path'])
        polys = {tag: audit.frozen.previous.polygon_points(p, contract, groups) for tag, contract in contracts.items()}
        first = [caption(image, identity + ' ORIGINAL', 'Source pixels unchanged; display enlarged only')]
        second = []
        for tag in contracts:
            row = by_key[(tag, identity, 'forehead_brow')]
            title = f"{tag}: brow {100 * float(row['brow_proxy_coverage']):.2f}%; cross {row['self_intersection']}"
            overlay = drawn(image, p, polys[tag], crossing=True)
            first.append(panel_large(overlay, title))
            second.append(panel_large(drawn(image, p, polys[tag], crossing=True, labels=True), tag + ': vertex ORDER, not MP index'))
        info = [identity, 'Upper FACE_OVAL retained; magenta = native brow proxy.',
            'Orange forehead, green/viewer-left cheek, blue/viewer-right cheek, purple nose/mouth.',
            'Red = proper crossing edges; white cross = intersection.',
            'Numbers = polygon vertex order. Full A68/MP/offsets in CSV.',
            'No hull, clipping to face oval, warp or pixel subtraction.',
            'Candidate removes v0.3 lower-brow offset; not active.',
            *reasons]
        second.append(wrap_panel('Scope / interpretation', info))
        canvas = np.vstack([np.hstack(first), np.hstack(second)])
        path = out / 'contact_sheets' / (identity + '_before_after.png')
        assert cv2.imwrite(str(path), canvas)
        mini_panels.append(np.hstack(first))
        records.append(dict(image_id=identity, source=source['source'], image_sha256=source['image_hash'],
            landmark_row_sha256=audit.hashlib.sha256(p.tobytes()).hexdigest(), reasons=reasons,
            contact_sheet=str(path.relative_to(audit.ROOT)), review_status='VISUAL_REVIEW_REQUIRED_NOT_ANATOMICAL_GROUND_TRUTH'))
    for j in range(0, len(mini_panels), 4):
        assert cv2.imwrite(str(out / 'contact_sheets' / f'overview_{j // 4 + 1:02}.png'), np.vstack(mini_panels[j:j + 4]))
    # A68:MP labels on all four regions, two independent source examples.
    for identity in ['cfd_final_00001', 'hf_merged_00001']:
        i = positions[identity]; p = points[i]; image = cv2.imread(images[names[i]]['image_path'])
        candidate = audit.frozen.previous.polygon_points(p, contracts['candidate_v0_4'], groups)
        panels = []
        inverse = {mp: k for k, mp in enumerate(indices)}
        for j, region in enumerate(audit.REGIONS):
            result = cv2.resize(image, (768, 768), interpolation=cv2.INTER_NEAREST)
            v = np.rint(candidate[region] * 3).astype(int)
            cv2.polylines(result, [v.astype(np.int32)], True, COLORS[j], 2, cv2.LINE_AA)
            for order, ((x, y), definition) in enumerate(zip(v, contracts['candidate_v0_4']['polygons'][region])):
                mp = definition['mediapipe_index']; prefix = f'A{inverse[mp]}:' if mp in inverse else ''
                cv2.putText(result, f'{order} {prefix}MP{mp}', (int(x) + 3, int(y) - 3), 0, .38, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(result, f'{order} {prefix}MP{mp}', (int(x) + 3, int(y) - 3), 0, .38, (255, 255, 255), 1, cv2.LINE_AA)
            panels.append(result)
        assert cv2.imwrite(str(out / 'contact_sheets' / (identity + '_all_regions_A_MP.png')), np.vstack([np.hstack(panels[:2]), np.hstack(panels[2:])]))
    audit.write_json(out / 'contact_sheet_selection.json', dict(schema_id='C1_REMEDIATION_VISUAL_SCOPE_v0.4.0',
        strategy='Required cases + fixed examples + deterministic census extrema; never retrieval metrics',
        count=len(records), images=records, annotated_all_regions_examples=2,
        full_corpus_manually_anatomically_reviewed=False, anatomy_status='ANATOMY_PROVISIONAL'))
    print('Rendered', len(records), 'before/after case sheets; anatomical acceptance remains unverified', flush=True)


if __name__ == '__main__':
    main()
