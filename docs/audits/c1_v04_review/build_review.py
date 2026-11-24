"""Prepare human review evidence only; no LBP, fitting, ranking or activation."""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import html
import json
import random
import shutil
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docs/audits/c1_remediation_tools'))
import audit_remediation as source

OUT = Path(__file__).resolve().parent
SEED = 24042026
V02 = 'C1_ROI_RAW_CONTRACT_v0.2.0'
V04 = 'C1_ROI_ANATOMICAL_CANDIDATE_v0.4.0'
PINS = {V02: source.ROI_PIN, V04: 'c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39'}
REGIONS = source.REGIONS
COLORS = [(0, 170, 250), (60, 200, 70), (240, 160, 20), (200, 60, 190)]
QUESTIONS = ['covers_described_anatomy', 'cuts_important_part', 'excess_non_target_material',
             'expression_boundary_reasonable', 'pdf_landmark_verification_needed']
FIELDS = ['image_id', 'roi_name', 'contract_version', 'geometry_status', 'anatomy_review_status',
          'reviewer', 'review_date', 'evidence_path', 'reason', 'decision_notes',
          *QUESTIONS, 'left_right_reference', 'occlusion_observation', 'reviewer_authority_evidence',
          'decision_evidence_path', 'decision_evidence_sha256', 'contract_content_sha256', 'image_sha256']
OBSERVED = {
    'cfd_final_00069': ['open_mouth_visible; prior_agent_observation_not_review_decision'],
    'cfd_final_00268': ['wide_eyes_open_mouth_visible; prior_agent_observation_not_review_decision'],
    'cfd_final_00112': ['forehead_hair_visible; prior_agent_observation_not_review_decision'],
    'hf_merged_00055': ['forehead_hair_visible; prior_agent_observation_not_review_decision'],
    'hf_merged_00198': ['glasses_visible; prior_agent_observation_not_review_decision'],
    'hf_merged_00209': ['head_covering_visible; missing_B_hair_is_separate; prior_agent_observation'],
    'hf_merged_00311': ['forehead_hair_visible; prior_agent_observation_not_review_decision'],
    'hf_merged_00333': ['secondary_faces_visible; prior_confirmed_dataset_violation'],
    'hf_merged_00561': ['secondary_face_and_forehead_hair_visible; prior_confirmed_dataset_violation'],
    'hf_merged_00694': ['head_covering_and_glasses_visible; prior_agent_observation_not_review_decision'],
    'hf_merged_00722': ['hand_over_mouth_visible; prior_confirmed_dataset_violation'],
}


def check_baseline():
    baseline = source.read_json(OUT / 'baseline_before.json')
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or source.digest(p) != h]
    if changed: raise ValueError('Protected artifacts changed: ' + repr(changed[:5]))
    return baseline


def contracts():
    pair = {V02: source.read_json(source.OLD / 'contract_v0_2.json'),
            V04: source.read_json(source.OUT / 'candidate_contract_v0_4.json')}
    for version, contract in pair.items():
        content = dict(contract); stored = content.pop('content_sha256')
        if stored != PINS[version] or source.canonical(content) != PINS[version] or contract['schema_id'] != version:
            raise ValueError('Pinned contract mismatch: ' + version)
    return pair


def select_images(metrics):
    reasons = defaultdict(list)
    for key in source.NEGATIVE: reasons[key].append('required_v02_self_intersection')
    for row in source.read_csv(source.OUT / 'native_brow_outside_points.csv'):
        reasons[row['image_id']].append('required_native_brow_point_outside_v04')
    for key in ['hf_merged_00333', 'hf_merged_00561', 'hf_merged_00722']:
        reasons[key].append('required_confirmed_dataset_violation')
    for key in ['cfd_final_00112', 'hf_merged_00055', 'hf_merged_00311', 'hf_merged_00561']:
        reasons[key].append('required_prior_visible_forehead_hair_case')
    for key in ['hf_merged_00198', 'hf_merged_00694']: reasons[key].append('required_prior_visible_glasses_case')
    for key in ['hf_merged_00209', 'hf_merged_00694']: reasons[key].append('required_prior_visible_head_covering_case')
    for key in ['cfd_final_00069', 'cfd_final_00268']: reasons[key].append('required_visible_expression_geometry_case_no_emotion_label')
    for key in ['cfd_final_00001', 'hf_merged_00001']: reasons[key].append('fixed_CFD_HF_reference')
    extrema = []
    for tag in ['v0_2', 'candidate_v0_4']:
        rows = [r for r in metrics if r['variant'] == tag and r['region'] == 'forehead_brow']
        for field in ['continuous_area_px2', 'raw_mask_pixels']:
            for maximum in [False, True]:
                r = sorted(rows, key=lambda r: ((-1 if maximum else 1) * float(r[field]), r['image_id']))[0]
                label = tag + ':' + field + (':maximum' if maximum else ':minimum')
                reasons[r['image_id']].append(label)
                extrema.append(dict(variant=tag, field=field, extremum='maximum' if maximum else 'minimum', image_id=r['image_id'], value=float(r[field])))
    mandatory = sorted(reasons)
    sources = {r['image_id']: r['source'].lower() for r in metrics}
    rng = random.Random(SEED)
    selected = set(mandatory)
    for group in ['cfd', 'hf']:
        present = sum(sources[k] == group for k in selected)
        if present > 50: raise ValueError('Mandatory cases exceed source quota')
        pool = sorted(k for k, src in sources.items() if src == group and k not in selected)
        for key in rng.sample(pool, 50 - present):
            reasons[key].append('seeded_random_source_balanced_fill'); selected.add(key)
    assert len(selected) == 100
    return [(k, sorted(set(reasons[k]))) for k in sorted(selected)], mandatory, extrema


def png(path, pixels):
    if path.exists(): raise FileExistsError(str(path))
    if not cv2.imwrite(str(path), pixels): raise OSError('Cannot write ' + str(path))


def framed(image, title, side=384):
    panel = np.full((side + 42, side, 3), 250, np.uint8)
    panel[29:side + 29] = cv2.resize(image, (side, side), interpolation=cv2.INTER_NEAREST)
    cv2.putText(panel, title, (5, 20), 0, .41, (20, 20, 20), 1, cv2.LINE_AA)
    return panel


def overlay(image, polygons, points, crossing=False):
    result = cv2.resize(image, (768, 768), interpolation=cv2.INTER_NEAREST)
    for j, region in enumerate(REGIONS):
        v = np.rint(polygons[region] * 3).astype(np.int32)
        cv2.polylines(result, [v], True, COLORS[j], 2, cv2.LINE_AA)
        if crossing:
            for entry in source.segment_intersections(polygons[region]):
                for key in ['edge_a', 'edge_b']:
                    a, b = entry[key]; cv2.line(result, tuple(v[a]), tuple(v[b]), (0, 0, 255), 3, cv2.LINE_AA)
                x, y = np.rint(np.array(entry['intersection_xy']) * 3).astype(int)
                cv2.drawMarker(result, (x, y), (255, 255, 255), cv2.MARKER_TILTED_CROSS, 16, 2)
    for chain in [source.frozen.BROW_LEFT, source.frozen.BROW_RIGHT]:
        cv2.polylines(result, [np.rint(points[chain] * 3).astype(np.int32)], True, (220, 80, 220), 1, cv2.LINE_AA)
    return result


def landmark_plate(image, points, indices, definitions, polygons):
    plate = np.full((960, 1536, 3), 250, np.uint8)
    plate[90:858, :768] = cv2.resize(image, (768, 768), interpolation=cv2.INTER_NEAREST)
    cv2.putText(plate, 'A68 order + related MP indices (0-based); viewer left/right; NOT_REVIEWED', (10, 35), 0, .7, (0, 0, 0), 1, cv2.LINE_AA)
    inverse = {mp: j for j, mp in enumerate(indices)}
    auxiliary = sorted({v['mediapipe_index'] for c in definitions.values() for poly in c['polygons'].values() for v in poly} - set(indices))
    for j, mp in enumerate(indices):
        x, y = np.rint(points[mp] * 3).astype(int); y += 90
        cv2.circle(plate, (x, y), 2, (0, 255, 255), -1)
        cv2.putText(plate, str(j), (x + 2, y - 2), 0, .35, (0, 0, 0), 1, cv2.LINE_AA)
        col, row = j // 34, j % 34
        cv2.putText(plate, f'A{j:02} = MP{mp:03}', (780 + col * 240, 78 + row * 24), 0, .48, (20, 20, 20), 1, cv2.LINE_AA)
    for j, mp in enumerate(auxiliary):
        x, y = np.rint(points[mp] * 3).astype(int); y += 90
        cv2.circle(plate, (x, y), 2, (255, 180, 0), -1)
        cv2.putText(plate, 'M' + str(mp), (x + 2, y - 2), 0, .33, (180, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(plate, f'MP{mp:03}', (1280, 78 + j * 24), 0, .46, (160, 30, 0), 1, cv2.LINE_AA)
    forehead = polygons[V04]['forehead_brow'].astype(np.float32)
    for mp in sorted(set(source.frozen.BROW_LEFT + source.frozen.BROW_RIGHT)):
        if cv2.pointPolygonTest(forehead, tuple(map(float, points[mp])), False) < 0:
            x, y = np.rint(points[mp] * 3).astype(int)
            cv2.drawMarker(plate, (x, y + 90), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 18, 2)
    cv2.putText(plate, 'Yellow=A68; blue=M/MP auxiliary; red cross=native brow point outside v0.4', (12, 909), 0, .55, (20, 20, 20), 1, cv2.LINE_AA)
    cv2.putText(plate, 'Native membership is model evidence, not human anatomical annotation.', (12, 941), 0, .55, (20, 20, 20), 1, cv2.LINE_AA)
    return plate


def main():
    if (OUT / 'review_manifest.json').exists() or (OUT / 'contact_sheets').exists():
        raise FileExistsError('Existing review package; refuse overwrite')
    baseline = check_baseline(); pair = contracts()
    metrics = source.read_csv(source.OUT / 'roi_metrics.csv')
    metric_map = {(r['variant'], r['image_id'], r['region']): r for r in metrics}
    selection, mandatory, extrema = select_images(metrics)
    names, points, images, _, proof = source.frozen.previous.load_archive()
    positions = {Path(name).stem: i for i, name in enumerate(names)}
    groups, indices = source.frozen.previous.source_groups()
    (OUT / 'contact_sheets').mkdir()
    for filename in ['pdf_page8_X31.png', 'pdf_page8_X33.png']:
        shutil.copyfile(ROOT / 'docs/audits/evidence' / filename, OUT / 'reference' / filename)
    source.write_json(OUT / 'review_schema.json', dict(schema_id='C1_V04_HUMAN_REVIEW_SCHEMA_v1',
        required_fields=FIELDS, unique_key=['image_id', 'roi_name', 'contract_version'],
        anatomy_review_status=['ACCEPT', 'REJECT', 'UNCERTAIN', 'NOT_REVIEWED'],
        default_anatomy_review_status='NOT_REVIEWED', question_columns=QUESTIONS,
        question_values=['YES', 'NO', 'UNCERTAIN', 'NOT_ANSWERED'],
        left_right_reference_values=['VIEWER', 'IMAGE_SUBJECT', 'UNCERTAIN', 'NOT_ANSWERED'],
        note='Geometry and prior observations must never supply anatomy_review_status; evidence paths are relative to package root'))
    annotations, records, membership = [], [], []
    for n, (identity, reasons) in enumerate(selection, 1):
        i = positions[identity]; p = points[i]; name = names[i]; image_meta = images[name]
        folder = OUT / 'contact_sheets' / identity; folder.mkdir()
        image = cv2.imread(image_meta['image_path'], cv2.IMREAD_UNCHANGED)
        if source.digest(image_meta['image_path']) != image_meta['image_hash']: raise ValueError('Image hash changed')
        shutil.copyfile(image_meta['image_path'], folder / 'original.png')
        polygons = {v: source.frozen.previous.polygon_points(p, c, groups) for v, c in pair.items()}
        masks, measures, outside = {}, {}, {}
        for version, contract in pair.items():
            short = 'v02' if version == V02 else 'v04'; tag = 'v0_2' if version == V02 else 'candidate_v0_4'
            masks[version] = {}; measures[version] = {}; outside[version] = {}
            for region in REGIONS:
                mask = source.frozen.raw_mask(polygons[version][region]); masks[version][region] = mask
                frozen = metric_map[(tag, identity, region)]
                if source.hashlib.sha256(mask.tobytes()).hexdigest() != frozen['raw_mask_sha256']:
                    raise ValueError('Mask differs from frozen census: ' + identity + region)
                png(folder / (short + '_' + region + '_raw.png'), mask * 255)
                status = 'GEOMETRY_VALID' if frozen['geometry_valid'] == 'True' else 'GEOMETRY_INVALID_SELF_INTERSECTION'
                measures[version][region] = dict(geometry_status=status, raw_mask_pixels=int(frozen['raw_mask_pixels']),
                    eligible_centres=int(frozen['eligible_centres']), raw_mask_sha256=frozen['raw_mask_sha256'])
                source_nodes = {x['mediapipe_index'] for x in contract['polygons'][region]}
                relevant = source_nodes | (set(source.frozen.BROW_LEFT + source.frozen.BROW_RIGHT) if region == 'forehead_brow' else set())
                outside[version][region] = []
                for mp in sorted(set(indices) | relevant):
                    distance = cv2.pointPolygonTest(polygons[version][region].astype(np.float32), tuple(map(float, p[mp])), True)
                    role = 'GLOBAL_A68_CONTEXT_NOT_REQUIRED_INSIDE'
                    if mp in relevant: role = 'SOURCE_MP_RAW_POINT_OFFSET_MAY_MOVE'
                    if region == 'forehead_brow' and mp in set(source.frozen.BROW_LEFT + source.frozen.BROW_RIGHT):
                        role = 'NATIVE_BROW_MODEL_PROXY_NOT_GROUND_TRUTH'
                    membership.append(dict(image_id=identity, contract_version=version, roi_name=region,
                        index68=indices.index(mp) if mp in indices else '', mediapipe_index=mp,
                        x=float(p[mp, 0]), y=float(p[mp, 1]), inside_or_boundary=distance >= 0,
                        signed_distance_px=distance, point_role=role))
                    if mp in relevant and distance < 0:
                        outside[version][region].append(dict(mediapipe_index=mp, x=float(p[mp, 0]), y=float(p[mp, 1]),
                            signed_distance_px=distance, role=role))
                annotations.append(dict(image_id=identity, roi_name=region, contract_version=version,
                    geometry_status=status, anatomy_review_status='NOT_REVIEWED', reviewer='', review_date='',
                    evidence_path='contact_sheets/' + identity + '/index.html', reason='', decision_notes='',
                    **{q: 'NOT_ANSWERED' for q in QUESTIONS}, left_right_reference='NOT_ANSWERED',
                    occlusion_observation='', reviewer_authority_evidence='', decision_evidence_path='',
                    decision_evidence_sha256='', contract_content_sha256=PINS[version], image_sha256=image_meta['image_hash']))
        before = overlay(image, polygons[V02], p, crossing=True); after = overlay(image, polygons[V04], p)
        png(folder / 'polygons_v02.png', before); png(folder / 'polygons_v04.png', after)
        plate = landmark_plate(image, p, indices, pair, polygons); png(folder / 'landmarks.png', plate)
        changes, delta_panels = {}, []
        for region in REGIONS:
            old, new = masks[V02][region], masks[V04][region]
            added, removed = (new != 0) & (old == 0), (new == 0) & (old != 0)
            changes[region] = dict(added_pixels=int(added.sum()), removed_pixels=int(removed.sum()))
            png(folder / (region + '_added.png'), added.astype(np.uint8) * 255)
            png(folder / (region + '_removed.png'), removed.astype(np.uint8) * 255)
            delta = image.copy(); delta[added] = (0, 255, 0); delta[removed] = (0, 0, 255)
            png(folder / (region + '_change_overlay.png'), delta)
            delta_panels.append(framed(delta, region + ' +GREEN/-RED'))
        panels = [framed(image, identity + ' ORIGINAL'), framed(before, 'v0.2; red crossing = geometry only'),
                  framed(after, 'v0.4 CANDIDATE / NOT_REVIEWED'), framed(plate[:, :768], 'A68 + auxiliary MP; full plate in page')]
        panels += [framed(cv2.cvtColor(masks[V04][r] * 255, cv2.COLOR_GRAY2BGR), 'v0.4 RAW ' + r) for r in REGIONS]
        panels += delta_panels
        png(folder / 'contact.png', np.vstack([np.hstack(panels[j:j+4]) for j in (0, 4, 8)]))
        observed = OBSERVED.get(identity, ['NO_PRIOR_OBSERVATION_RECORDED_NOT_OCCLUSION_CLEARANCE'])
        record = dict(image_id=identity, filename=name, source=image_meta['source'], image_sha256=image_meta['image_hash'],
            landmark_row_sha256=source.hashlib.sha256(p.tobytes()).hexdigest(), landmark_archive_row_index=i,
            selection_reasons=reasons, mandatory=identity in mandatory, evidence_path='contact_sheets/' + identity + '/index.html',
            measurements=measures, pixel_changes=changes, relevant_points_outside=outside,
            prior_observed_risks=observed, observation_authority='PRIOR_AGENT_OBSERVATIONS_OR_DATASET_AUDIT; NOT HUMAN ROI ACCEPTANCE',
            current_human_occlusion_observation='', anatomy_review_status='NOT_REVIEWED',
            contract_hashes=PINS, source_landmarks_provenance='authenticated saved478; audit_remeasurement, not historical alignment proof')
        source.write_json(folder / 'evidence.json', record)
        sections = ''
        for label, file in [('Original unchanged', 'original.png'), ('v0.2 polygons', 'polygons_v02.png'), ('v0.4 candidate polygons', 'polygons_v04.png'), ('A68 and related MP / red outside brow points', 'landmarks.png')]:
            sections += f'<h2>{html.escape(label)}</h2><a href="{file}"><img src="{file}"></a>'
        for version, short in [(V02, 'v02'), (V04, 'v04')]:
            sections += '<h2>' + version + ' raw masks (independent overlap retained)</h2><div class="grid">'
            for region in REGIONS:
                file = short + '_' + region + '_raw.png'
                sections += f'<figure><figcaption>{region}: {measures[version][region]["geometry_status"]}</figcaption><a href="{file}"><img src="{file}"></a></figure>'
            sections += '</div>'
        for region in REGIONS:
            file = region + '_change_overlay.png'
            sections += f'<h3>{region}: added GREEN, removed RED</h3><a href="{file}"><img src="{file}"></a>'
        doc = f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>{identity} ROI review</title>
<style>body{{font:16px system-ui;max-width:1500px;margin:24px auto;padding:16px}}img{{max-width:100%;image-rendering:auto}}.grid{{display:grid;grid-template-columns:repeat(4,1fr)}}figure{{margin:8px}}pre{{white-space:pre-wrap}}.pending{{background:#fff0bf;padding:12px}}</style>
<a href="../../index.html">Danh sách100 ảnh</a><h1>{identity}</h1><p class="pending">NOT_REVIEWED — v0.4 chưa kích hoạt. Geometry không phải anatomy approval.</p>
<p>Trái/phải theo người xem; index0-based. Mask v0.2 tự giao chỉ để chẩn đoán. Nhấn ảnh để xem đủ độ phân giải.</p>
<p>Quan sát trước đây, chưa phải đánh giá của reviewer: {html.escape('; '.join(observed))}</p>
<p>Reviewer phải ghi nhận che khuất trên phiếu; không có cảnh báo không có nghĩa ảnh đã được clearance.</p>
<a href="evidence.json">Tọa độ điểm liên quan ngoài polygon, số pixel và hash</a> · <a href="../../review_annotations.csv">Phiếu CSV800 dòng</a>
{sections}<h2>Điểm liên quan nằm ngoài polygon</h2><pre>{html.escape(json.dumps(outside,ensure_ascii=False,indent=2))}</pre>
<p>Điểm nguồn chưa offset có thể ở ngoài ROI một cách có chủ đích; không coi mọi điểm A68 ngoài một vùng là lỗi.</p></html>'''
        (folder / 'index.html').write_text(doc, encoding='utf-8')
        records.append(record)
        if n % 10 == 0: print('Rendered', n, '/100 review cases; anatomy NOT_REVIEWED', flush=True)
    source.save_csv(OUT / 'review_annotations.csv', annotations)
    source.save_csv(OUT / 'landmark_membership.csv', membership)
    with (OUT / 'reviewer_authorities.csv').open('x', encoding='utf-8', newline='') as stream:
        csv.writer(stream).writerow(['reviewer', 'role', 'appointment_evidence_path', 'appointment_evidence_sha256', 'authority_confirmation_status'])
    manifest = dict(schema_id='C1_V04_ANATOMICAL_REVIEW_MANIFEST_v1', created_date='2026-11-24', timezone='Asia/Saigon',
        seed=SEED, selection_algorithm='Mandatory + extrema then random.Random(seed).sample(sorted remaining IDs), source CFD then HF;50 each',
        source_counts=dict(Counter(r['source'] for r in records)), count=100, mandatory_ids=mandatory, extrema=extrema,
        selected_ids=[r['image_id'] for r in records], contract_hashes=PINS, anatomy_review_status='NOT_REVIEWED',
        annotation_rows=800, annotation_rows_per_contract=400, reviewer_authorities_recorded=0,
        selected_review_is_not_full_corpus_anatomical_certification=True, candidate_activated=False,
        source_proof=proof, protected_file_count=len(baseline), renderer_environment=dict(numpy=np.__version__, opencv=cv2.__version__, python=sys.version),
        source_files_sha256={str(path.relative_to(ROOT)): source.digest(path) for path in [source.OUT / 'roi_metrics.csv', source.OUT / 'native_brow_outside_points.csv', source.OUT / 'visual_observations.json']},
        images=records)
    source.write_json(OUT / 'review_manifest.json', manifest)
    rows_html = ''.join('<tr><td><a href="' + r['evidence_path'] + '">' + r['image_id'] + '</a></td><td>' + r['source'] + '</td><td>' + html.escape('; '.join(r['selection_reasons'])) + '</td><td>NOT_REVIEWED</td></tr>' for r in records)
    index = '<!doctype html><html lang="vi"><meta charset="utf-8"><title>C1 v0.4 anatomy review100</title><style>body{font:16px system-ui;max-width:1300px;margin:24px auto}td,th{border:1px solid #ccc;padding:8px}table{border-collapse:collapse}input{padding:10px;width:400px}</style><h1>C1 v0.4 — review100 ảnh</h1><p>Hồ sơ chưa có đánh giá/chấp thuận của con người. 800 dòng CSV:100×4 vùng×2 contract, NOT_REVIEWED.</p><p><a href="../C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md">Protocol</a> · <a href="review_annotations.csv">Phiếu CSV</a> · <a href="reference/pdf_page8_X31.png">Hình PDF68</a> · <a href="reference/pdf_sections_2_2_2_4.txt">PDF2.2/2.4</a></p><input id="filter" placeholder="Lọc ID hoặc lý do chọn"><table><thead><tr><th>Ảnh</th><th>Nguồn</th><th>Lý do</th><th>Trạng thái lúc tạo</th></tr></thead><tbody>' + rows_html + '</tbody></table><script>document.getElementById("filter").addEventListener("input",function(){const q=this.value.toLowerCase();for(const r of document.querySelectorAll("tbody tr"))r.hidden=!r.textContent.toLowerCase().includes(q);});</script></html>'
    (OUT / 'index.html').write_text(index, encoding='utf-8')
    print('Prepared100 images /800 NOT_REVIEWED annotations; no feature extraction', flush=True)


if __name__ == '__main__': main()
