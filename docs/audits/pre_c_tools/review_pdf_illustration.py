"""Measure marker centres in the embedded CFD figure, without editing the PDF.

The raster has no MP identifiers. These measurements document differences from
the illustration only and cannot identify a replacement canonical MP mapping.
"""
from pathlib import Path
import sys
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, write_json

DOC = ROOT / 'docs/audits'
E = DOC / 'pre_c_evidence'
FIGURE = DOC / 'evidence/pdf_page8_X31.png'


def components(mask):
    remaining = set(zip(*np.where(mask)))
    result = []
    while remaining:
        pending = [remaining.pop()]
        found = []
        while pending:
            y, x = pending.pop()
            found.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    adjacent = (y+dy, x+dx)
                    if adjacent in remaining:
                        remaining.remove(adjacent)
                        pending.append(adjacent)
        ys, xs = np.array(found).T
        result.append(dict(count=len(found), x=float(xs.mean()), y=float(ys.mean()),
                           width=int(xs.max()-xs.min()+1), height=int(ys.max()-ys.min()+1)))
    return result


def main():
    full = np.array(Image.open(FIGURE).convert('RGB'))
    # Right panel, based on visible frame borders in the embedded 2048x824 image.
    x0, y0, width, height = 1373, 98, 660, 662
    panel = full[y0:y0+height, x0:x0+width]
    colors = dict(jaw=[[0, 180, 255]], nose=[[50, 205, 50], [34, 139, 34]])
    cores = components(np.all(panel >= 250, axis=2))
    cores = [p for p in cores if p['width'] <= 5 and p['height'] <= 5]
    groups = {}
    for name, color in colors.items():
        centres = []
        for core in cores:
            x, y = round(core['x']), round(core['y'])
            ring = panel[max(0,y-4):y+5, max(0,x-4):x+5].astype(float)
            if any(np.any(np.linalg.norm(ring-c, axis=2) < 35) for c in color):
                centres.append(dict(core))
        for p in centres:
            p['source_x_approx'] = (p['x']+.5)*256/width-.5
            p['source_y_approx'] = (p['y']+.5)*256/height-.5
        groups[name] = sorted(centres, key=lambda p: (p['y'], p['x']))
    assert len(groups['jaw']) == 17, len(groups['jaw'])
    assert len(groups['nose']) == 9, len(groups['nose'])
    points = np.load(E / 'cfd_final_00001_points478.npy')
    nose_bridge_end = groups['nose'][3]
    nose_base_centre = min(groups['nose'][4:], key=lambda p: abs(p['source_x_approx']-nose_bridge_end['source_x_approx']))
    jaw_ends = sorted(groups['jaw'][:2], key=lambda p: p['source_x_approx'])
    comparisons = []
    for label, index68, mp_index, measured in [
            ('jaw_start_left_in_image',0,234,jaw_ends[0]),
            ('jaw_end_right_in_image',16,454,jaw_ends[1]),
            ('fourth_bridge_marker',30,1,nose_bridge_end),
            ('middle_of_five_base_markers',33,4,nose_base_centre)]:
        xy = [measured['source_x_approx'],measured['source_y_approx']]
        current = points[mp_index].tolist()
        comparisons.append(dict(label=label, index68_zero_based=index68,
            current_mp_index=mp_index, illustration_xy_approx=xy,
            current_xy=current, y_current_minus_illustration=float(current[1]-xy[1])))
    result = dict(figure=str(FIGURE.relative_to(ROOT)), sha256=digest(FIGURE),
                  panel_bounds=[x0, y0, width, height],
                  method='Small near-white marker cores with nearby matching colored ring; approximate panel-to-256 scaling',
                  caveat='Raster reading only, not MP ID assignment, canonical annotation or a mapping correction',
                  approximate_reading_uncertainty_source_pixels=1.0,
                  colors=colors, marker_centres=groups, comparisons=comparisons,
                  nose_base_minus_bridge_y_illustration=float(nose_base_centre['source_y_approx']-nose_bridge_end['source_y_approx']),
                  nose_base_minus_bridge_y_current=float(points[4,1]-points[1,1]))
    write_json(E / 'pdf_illustration_measurements.json', result)
    print(json.dumps(dict(marker_counts={k: len(v) for k,v in groups.items()},
                          comparisons=comparisons,
                          illustration_base_minus_bridge_y=result['nose_base_minus_bridge_y_illustration'],
                          current_base_minus_bridge_y=result['nose_base_minus_bridge_y_current']), indent=2))


if __name__ == '__main__':
    main()
