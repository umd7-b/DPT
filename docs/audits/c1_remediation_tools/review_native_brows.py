"""Separate fractional landmark coverage from integer proxy-pixel coverage."""
import cv2
import numpy as np

import audit_remediation as audit


def main():
    if (audit.OUT / 'native_brow_outside_points.csv').exists():
        raise FileExistsError('Native brow review already exists')
    names, points, images, _, _ = audit.frozen.previous.load_archive()
    groups, _ = audit.frozen.previous.source_groups()
    contract = audit.read_json(audit.OUT / 'candidate_contract_v0_4.json')
    rows, panels = [], []
    nodes = sorted(set(audit.frozen.BROW_LEFT + audit.frozen.BROW_RIGHT))
    for name, p in zip(names, points):
        v = audit.frozen.previous.polygon_points(p, contract, groups)['forehead_brow']
        contour = v.astype(np.float32)
        missing = [(mp, cv2.pointPolygonTest(contour, tuple(map(float, p[mp])), True)) for mp in nodes
                   if cv2.pointPolygonTest(contour, tuple(map(float, p[mp])), False) < 0]
        if not missing: continue
        identity = images[name]['image_id']
        image = cv2.imread(images[name]['image_path'])
        picture = cv2.resize(image, (768, 768), interpolation=cv2.INTER_NEAREST)
        cv2.polylines(picture, [np.rint(v * 3).astype(np.int32)], True, (0, 170, 255), 2, cv2.LINE_AA)
        for chain in (audit.frozen.BROW_LEFT, audit.frozen.BROW_RIGHT):
            cv2.polylines(picture, [np.rint(p[chain] * 3).astype(np.int32)], True, (220, 80, 220), 1, cv2.LINE_AA)
        for mp, distance in missing:
            x, y = np.rint(p[mp] * 3).astype(int)
            cv2.drawMarker(picture, (x, y), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 16, 2)
            cv2.putText(picture, f'MP{mp} outside {abs(distance):.4f}px', (max(4, min(x, 470)), max(20, y - 12)), 0, .48, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(picture, f'MP{mp} outside {abs(distance):.4f}px', (max(4, min(x, 470)), max(20, y - 12)), 0, .48, (255, 255, 255), 1, cv2.LINE_AA)
            rows.append(dict(image_id=identity, image_sha256=images[name]['image_hash'], mediapipe_index=mp,
                x=float(p[mp, 0]), y=float(p[mp, 1]), signed_distance_to_candidate_boundary=distance,
                role='native_model_point_not_anatomical_ground_truth', anatomy_status='ANATOMY_PROVISIONAL'))
        panel = np.full((823, 768, 3), 250, np.uint8)
        panel[35:803] = picture
        cv2.putText(panel, identity + ': fractional native node OUTSIDE candidate', (10, 24), 0, .6, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(panel, 'Model-proxy discrepancy; integer coverage can still be 100%; anatomy UNVERIFIED', (10, 819), 0, .42, (0, 0, 0), 1, cv2.LINE_AA)
        panels.append(panel)
    audit.save_csv(audit.OUT / 'native_brow_outside_points.csv', rows)
    assert len(panels) == 4
    assert cv2.imwrite(str(audit.OUT / 'contact_sheets/native_brow_fractional_exceptions.png'), np.vstack([np.hstack(panels[:2]), np.hstack(panels[2:])]))
    audit.write_json(audit.OUT / 'native_brow_point_summary.json', dict(images_with_points_outside=len(panels),
        affected_images=[r['image_id'] for r in rows], native_points_checked=1438 * 20,
        all_other_points_inside=True, no_contract_adjustment_after_this_measurement=True,
        explanation='Point containment is continuous; proxy coverage counts integer raster pixels. Neither is annotation.'))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
