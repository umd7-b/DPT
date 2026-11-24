"""Independent scalar oracle. Intentionally imports no target extractor/helpers.

EXPERIMENTAL_TECHNICAL_TRIAL; ROI_ANATOMY_STATUS=PROVISIONAL.
Uses integer grayscale, enumerated rotations, explicit support and scalar lerps.
"""
import math
import cv2
import numpy as np


def codebook():
    table = [58] * 256
    table[0], table[255] = 0, 57
    for length in range(1, 8):
        base = (1 << length) - 1
        for rotation in range(8):
            word = ((base >> rotation) | (base << (8 - rotation))) & 255
            table[word] = 1 + 8 * (length - 1) + rotation
    return table


def gray_image(bgr):
    return np.array([[(1868 * int(b) + 9617 * int(g) + 4899 * int(r) + 8192) // 16384
                      for b, g, r in row] for row in bgr], dtype=np.float64)


def support_points():
    # Explicit fixture independent of target support generation/erosion.
    return [(x, y) for y, row in [(-2, [-2, -1, 0, 1, 2]), (-1, [-2, -1, 1, 2]),
                                 (0, [-2, 0, 2]), (1, [-2, -1, 1, 2]), (2, [-2, -1, 0, 1, 2])]
            for x in row]


def mask_from_vertices(vertices, shape=(256, 256)):
    contour = np.array(vertices, dtype=np.float32)
    # Deliberately scans the full image instead of production bounding box.
    return np.array([[int(cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0)
                      for x in range(shape[1])] for y in range(shape[0])], dtype=np.uint8)


def centres(mask):
    height, width = mask.shape
    footprint = support_points()
    return [(x, y) for y in range(height) for x in range(width) if mask[y, x]
            and all(0 <= x + dx < width and 0 <= y + dy < height and mask[y + dy, x + dx]
                    for dx, dy in footprint)]


def neighbours(gray, x, y):
    root = math.sqrt(2.)
    offsets = [(2., 0.), (root, -root), (0., -2.), (-root, -root),
               (-2., 0.), (-root, root), (0., 2.), (root, root)]
    details = []
    for dx, dy in offsets:
        qx, qy = float(x) + dx, float(y) + dy
        x0, x1, y0, y1 = math.floor(qx), math.ceil(qx), math.floor(qy), math.ceil(qy)
        if not (0 <= x0 <= x1 < gray.shape[1] and 0 <= y0 <= y1 < gray.shape[0]):
            raise ValueError('No padding in oracle')
        tx, ty = qx - x0, qy - y0
        a, b, c, d = map(float, (gray[y0, x0], gray[y0, x1], gray[y1, x0], gray[y1, x1]))
        upper, lower = a + tx * (b - a), c + tx * (d - c)
        intensity = upper + ty * (lower - upper)
        details.append(dict(x=qx, y=qy, floor_ceil=[x0, x1, y0, y1], stencil_gray=[a, b, c, d],
                            tx=tx, ty=ty, horizontal=[upper, lower], gp=intensity,
                            bit=int(intensity >= float(gray[y, x]))))
    return details


def raw_code(gray, x, y):
    return sum(item['bit'] * (2 ** p) for p, item in enumerate(neighbours(gray, x, y)))


def histogram(gray, mask):
    selected = centres(mask)
    table, counts = codebook(), [0] * 59
    for x, y in selected:
        counts[table[raw_code(gray, x, y)]] += 1
    return np.array(counts, dtype=np.uint64), np.array([n / len(selected) for n in counts], dtype=np.float64), selected
