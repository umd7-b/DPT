"""Audit-only mapping/geometry evidence; never write extractor or gallery files."""
from pathlib import Path
import importlib
import importlib.util
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_csv, save_csv, write_json

import cv2
import mediapipe as mp
import numpy as np
from features.A_geometry.src import geometry_features as g
from features.A_geometry.src import map_68_landmarks as mapping

E = ROOT / 'docs/audits/pre_c_evidence'
DATA = Path('D:/TuNam4/dataset_HF_CFD_final/images')
GROUPS = ['JAW', 'LEFT_EYEBROW', 'RIGHT_EYEBROW', 'NOSE', 'LEFT_EYE', 'RIGHT_EYE', 'MOUTH']
TARGETS = {'JAW': 'FACE_LANDMARKS_FACE_OVAL', 'LEFT_EYEBROW': 'FACE_LANDMARKS_RIGHT_EYEBROW',
           'RIGHT_EYEBROW': 'FACE_LANDMARKS_LEFT_EYEBROW', 'NOSE': 'FACE_LANDMARKS_NOSE',
           'LEFT_EYE': 'FACE_LANDMARKS_RIGHT_EYE', 'RIGHT_EYE': 'FACE_LANDMARKS_LEFT_EYE',
           'MOUTH': 'FACE_LANDMARKS_LIPS'}


def overlay(image, points, name):
    # Full image, enlarged only for audit labels. No source crop or replacement.
    scale = 6
    side = image.shape[0] * scale
    canvas = np.full((side + 70, side + 600, 3), 255, np.uint8)
    canvas[70:, :side] = cv2.resize(image, (side, side), interpolation=cv2.INTER_NEAREST)
    cv2.putText(canvas, name + ' | A68 index : MP478 index | audit only', (10, 28), 0, .7, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(canvas, 'Full source frame. Native contour membership does not certify a canonical 68 mapping.', (10, 55), 0, .55, (0, 0, 0), 1)
    used = []
    palette = [(0, 170, 255), (180, 0, 180), (180, 0, 180), (20, 180, 20), (255, 100, 0), (255, 100, 0), (0, 0, 220)]
    index = 0
    for group, color in zip(GROUPS, palette):
        for mp_id in getattr(g, group):
            x, y = points[mp_id] * scale
            x, y = int(round(x)), int(round(y)) + 70
            label = f'{index}:{mp_id}'
            tw, th = cv2.getTextSize(label, 0, .5, 1)[0]
            chosen = None
            for radius in (10, 25, 45, 65, 90, 120, 160):
                for angle in (0, 180, 90, 270, 45, 135, 225, 315):
                    tx = int(x + radius * math.cos(math.radians(angle)))
                    ty = int(y + radius * math.sin(math.radians(angle)))
                    rect = (tx - 2, ty - th - 3, tx + tw + 2, ty + 4)
                    if rect[0] < 0 or rect[1] < 73 or rect[2] >= side or rect[3] >= side + 70:
                        continue
                    if any(not (rect[2] < r[0] or rect[0] > r[2] or rect[3] < r[1] or rect[1] > r[3]) for r in used):
                        continue
                    chosen = tx, ty, rect
                    break
                if chosen:
                    break
            if chosen:
                tx, ty, rect = chosen
                used.append(rect)
                cv2.line(canvas, (x, y), (tx, ty), color, 1, cv2.LINE_AA)
                cv2.rectangle(canvas, rect[:2], rect[2:], (255, 255, 255), -1)
                cv2.putText(canvas, label, (tx, ty), 0, .5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.circle(canvas, (x, y), 4, color, -1)
            cv2.putText(canvas, f'A[{index:02}] = MP{mp_id:03}  {group}', (side + 12, 90 + index * 21), 0, .44, color, 1, cv2.LINE_AA)
            index += 1
    assert index == 68
    cv2.imwrite(str(E / f'{Path(name).stem}_68_mp_overlay.png'), canvas)


def main():
    assert g.INDICES == mapping.LANDMARK_INDICES
    assert len(g.INDICES) == len(set(g.INDICES)) == 68 and all(0 <= i < 478 for i in g.INDICES)
    native = mp.tasks.vision.FaceLandmarksConnections
    native_module = importlib.import_module('mediapipe.tasks.python.vision.face_landmarker')
    edges = {key: [(int(c.start), int(c.end)) for c in getattr(native, key)]
             for key in set(TARGETS.values())}
    nodes = {key: {i for pair in values for i in pair} for key, values in edges.items()}
    groups = []
    for group in GROUPS:
        selected = getattr(g, group)
        target = TARGETS[group]
        groups.append(dict(group=group, selected=selected, native_contour=target,
            present=[i for i in selected if i in nodes[target]], absent=[i for i in selected if i not in nodes[target]],
            scope='Sparse contour membership only, not anatomical GT/canonical478-to68'))
    write_json(E / 'native_mediapipe_topology.json', dict(package_version=mp.__version__,
        package_source=str(native_module.__file__), package_source_sha256=digest(native_module.__file__),
        edges=edges, group_comparison=groups,
        official_source_url='https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py',
        canonical_reference_url='https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj',
        canonical_vertices_reviewed={'MP1': [0., -1.126865, 7.475604], 'MP4': [0., -.463170, 7.586580]},
        caveat='Canonical468 mesh coordinates are not an official canonical478-to68 mapping; master reference reviewed on 2026-11-23'))

    spec = importlib.util.spec_from_file_location('previous_scalar_oracles', ROOT / 'docs/audits/audit_tools/common.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    metadata = read_csv(ROOT / 'outputs/A_geometry/features/metadata.csv')
    raw = np.load(ROOT / 'outputs/A_geometry/features/features_A_raw.npy', allow_pickle=False)
    raw_index = {r['image_name']: i for i, r in enumerate(metadata)}
    results, values, point_table = [], [], []
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(g.MODEL_PATH)), num_faces=1)
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as model:
        for name in ['cfd_final_00001.png', 'hf_merged_00001.png', 'cfd_final_00069.png']:
            image = cv2.imread(str(DATA / name))
            found = model.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                data=np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))))
            assert len(found.face_landmarks) == 1 and len(found.face_landmarks[0]) == 478
            p478 = np.array([[lm.x * 256, lm.y * 256] for lm in found.face_landmarks[0]], np.float32)
            p68 = p478[g.INDICES]
            normalized, ipd = g.normalize_landmarks(p68)
            ratios = g.calculate_ratios(p68)
            expected, operands, centers = oracle.scalar_a2(p68)
            np.testing.assert_allclose(ratios, expected, rtol=2e-6, atol=2e-5)
            current = np.r_[normalized.flatten(), ratios]
            raw_error = float(np.max(np.abs(current - raw[raw_index[name]])))
            assert raw_error == 0
            np.save(E / f'{Path(name).stem}_points478.npy', p478, allow_pickle=False)
            overlay(image, p478, name)
            for j, (actual, wanted) in enumerate(zip(ratios, expected)):
                values.append(dict(image_name=name, a2_index=j + 1, feature_name=g.FEATURE_NAMES[j],
                    numerator=operands[j][0], denominator_before_epsilon=operands[j][1],
                    epsilon=1e-8 if j < 13 else 0., code_value=float(actual), scalar_oracle=float(wanted),
                    absolute_error=abs(float(actual) - wanted), unit='degrees' if j == 13 else 'dimensionless'))
            index = 0
            for group in GROUPS:
                for mp_id in getattr(g, group):
                    point_table.append(dict(image_name=name, index68_zero_based=index, index68_pdf_one_based=index + 1,
                        mediapipe_index=mp_id, code_group=group, native_contour=TARGETS[group],
                        on_native_sparse_contour=mp_id in nodes[TARGETS[group]],
                        x=float(p478[mp_id, 0]), y=float(p478[mp_id, 1])))
                    index += 1
            results.append(dict(image_name=name, raw_vector_max_error=raw_error, landmark_count=478,
                a2_max_scalar_error=float(np.max(np.abs(ratios - expected))),
                eye_left_mean6=centers[0], eye_right_mean6=centers[1], midpoint=centers[2], ipd=float(ipd),
                mp1=p478[1].astype(float).tolist(), mp4=p478[4].astype(float).tolist(),
                y_mp1_minus_mp4=float(p478[1, 1] - p478[4, 1])))
            # Nose-only annotations on the FULL frame; no image crop or source alteration.
            nose = cv2.resize(image, (1536, 1536), interpolation=cv2.INTER_NEAREST)
            for i, j in edges['FACE_LANDMARKS_NOSE']:
                a, b = tuple((p478[i] * 6).astype(int)), tuple((p478[j] * 6).astype(int))
                cv2.line(nose, a, b, (255, 230, 0), 2, cv2.LINE_AA)
            for branch in [g.NOSE[:4], g.NOSE[4:]]:
                for i, j in zip(branch, branch[1:]):
                    cv2.line(nose, tuple((p478[i] * 6).astype(int)), tuple((p478[j] * 6).astype(int)), (0, 0, 255), 2, cv2.LINE_AA)
            for index in [1, 4]:
                x, y = (p478[index] * 6).astype(int)
                cv2.circle(nose, (int(x), int(y)), 9, (0, 255, 255), 2)
                cv2.putText(nose, f'MP{index}', (int(x + 18), int(y)), 0, .8, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.rectangle(nose, (0, 0), (1535, 70), (255, 255, 255), -1)
            cv2.putText(nose, 'CYAN: native NOSE | RED: current A nose branches | A[30]=MP1; A[33]=MP4', (10, 30), 0, .65, (0, 0, 0), 1)
            cv2.putText(nose, name + ' | no proposed mapping applied', (10, 58), 0, .6, (0, 0, 0), 1)
            cv2.imwrite(str(E / f'{Path(name).stem}_nose_topology_fullframe.png'), nose)
    save_csv(E / 'mapping_points_review.csv', point_table)
    save_csv(E / 'a2_fresh_oracles.csv', values)
    write_json(E / 'mapping_verification.json', dict(unique_selected_points=68, groups_agree_between_source_files=True,
        selected_indices_below468=all(i < 468 for i in g.INDICES), group_results=groups, samples=results,
        mapping_modified=False, anatomical_canonical_mapping_verified=False))
    print(json.dumps(dict(groups=groups, real_images=results), indent=2))


if __name__ == '__main__':
    main()
