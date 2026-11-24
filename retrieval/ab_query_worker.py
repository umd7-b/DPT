"""Read-only adapters to existing A/B extractors, executed in separate venvs."""
import argparse
import json
from pathlib import Path
import sys
import sys

import numpy as np

from shared.paths import PROJECT_ROOT


def normalize_a(image):
    from features.A_geometry.src.geometry_features import extract_geometry
    raw, _, _, _ = extract_geometry(image)
    with np.load(PROJECT_ROOT / 'outputs/A_geometry/features/geometry_stats.npz', allow_pickle=False) as stats:
        mean, std = stats['mean'], stats['std']
    if mean.shape != (150,) or std.shape != (150,) or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std <= 0):
        raise ValueError('Invalid saved A normalization statistics')
    return (raw.astype(np.float64) - mean) / std


def normalize_b(image_path, skin_path=None, hair_path=None):
    import cv2
    from features.B_color.src.color_features import extract_color, transform
    from features.B_color.src.audit_color_inputs import load_mask
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None or image.shape != (256, 256, 3) or image.dtype != np.uint8:
        raise ValueError('New B query requires an aligned 256x256 uint8 BGR portrait')
    if skin_path is not None:
        skin, hair = load_mask(skin_path, (256, 256)), load_mask(hair_path, (256, 256))
        lineage = {'source': 'caller-supplied raw class-1/class-17 masks'}
    else:
        from features.B_color.src.batch_uniface import create_parser, make_masks
        parser, lineage = create_parser()  # Verified local weights; downloads disabled.
        masks = make_masks(parser.parse(image))
        skin, hair = masks['skin'], masks['hair']
    result = extract_color(image, skin, hair, min_pixels=100)
    status = dict(status='valid' if result.vector is not None else 'missing_B',
                  skin=result.skin, hair=result.hair, parser=lineage, fit_reused=True)
    if result.vector is None:
        return None, status
    with np.load(PROJECT_ROOT / 'outputs/B_color/color_features_full_v1/normalization_stats.npz', allow_pickle=False) as file:
        stats = {key: file[key].copy() for key in file.files}
    return transform(result.vector, stats), status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('a', 'b'), required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skin-mask', type=Path)
    parser.add_argument('--hair-mask', type=Path)
    args = parser.parse_args()
    if bool(args.skin_mask) != bool(args.hair_mask):
        parser.error('Both raw masks are required together')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.kind == 'a':
        vector, status = normalize_a(args.image), dict(status='valid', fit_reused=True)
    else:
        vector, status = normalize_b(args.image, args.skin_mask, args.hair_mask)
    status['python_executable'] = sys.executable
    status['python_executable'] = sys.executable
    dimension = 150 if args.kind == 'a' else 144
    if vector is not None:
        if vector.shape != (dimension,) or not np.isfinite(vector).all():
            raise ValueError('Invalid normalized query vector')
        np.save(args.output / f'query_{args.kind.upper()}_normalized.npy', vector, allow_pickle=False)
    (args.output / f'{args.kind}_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
