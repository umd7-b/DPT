"""V2-only query adapters to the original A/B extraction environments."""
import argparse
from pathlib import Path
import sys

import numpy as np
from shared.report_v2 import digest, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('a', 'b'), required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gallery', type=Path, required=True)
    parser.add_argument('--skin-mask', type=Path)
    parser.add_argument('--hair-mask', type=Path)
    args = parser.parse_args()
    if bool(args.skin_mask) != bool(args.hair_mask):
        parser.error('Both raw masks are required together')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.kind == 'a':
        from features.A_geometry.src import report_v2 as a
        from features.A_geometry.src.geometry_features import extract_geometry
        _, _, stats = a.load_gallery(args.gallery)
        raw, _, _, _ = extract_geometry(args.image)
        normalized = a.transform(raw, stats)
        np.save(args.output / 'query_A_raw.npy', raw, allow_pickle=False)
        status = dict(status='valid', schema_id=a.SCHEMA_ID, stats_sha256=digest(args.gallery / 'normalization_stats.npz'),
                      epsilon=float(stats['epsilon']), query_refit=False)
    else:
        import cv2
        from features.B_color.src import report_v2 as b
        from features.B_color.src.audit_color_inputs import load_mask
        _, _, ms, fs = b.load_gallery(args.gallery)
        image = cv2.imread(str(args.image), cv2.IMREAD_UNCHANGED)
        if image is None or image.shape != (256, 256, 3) or image.dtype != np.uint8:
            raise ValueError('New B query requires the existing aligned 256x256 uint8 portrait format')
        if args.skin_mask:
            skin_mask, hair_mask = load_mask(args.skin_mask, (256, 256)), load_mask(args.hair_mask, (256, 256))
            lineage = 'Caller-supplied raw class1/17 masks; semantic quality not certified'
        else:
            from features.B_color.src.batch_uniface import create_parser, make_masks
            model, lineage = create_parser()  # Local verified model only; no downloads.
            masks = make_masks(model.parse(image))
            skin_mask, hair_mask = masks['skin'], masks['hair']
        skin, hair, status = b.describe_regions(image, skin_mask, hair_mask)
        status.update(schema_id=b.SCHEMA_ID, moment_stats_sha256=digest(args.gallery / 'moment_normalization_stats.npz'),
            final_stats_sha256=digest(args.gallery / 'final_normalization_stats.npz'), query_refit=False, mask_lineage=lineage)
        normalized = None
        if status['status'] == 'valid':
            after = b.assemble_after_moments(skin, hair, ms)
            normalized = b.apply_stage(after, fs, 'final144')
            np.save(args.output / 'query_B_raw.npy', np.concatenate((skin, hair)), allow_pickle=False)
            np.save(args.output / 'query_B_after_moments.npy', after, allow_pickle=False)
    if normalized is not None:
        dimension = 150 if args.kind == 'a' else 144
        if normalized.shape != (dimension,) or not np.isfinite(normalized).all():
            raise ValueError('Invalid normalized v2 query descriptor')
        np.save(args.output / f'query_{args.kind.upper()}_normalized.npy', normalized, allow_pickle=False)
    status['python_executable'] = sys.executable
    write_json(args.output / f'{args.kind}_status.json', status)


if __name__ == '__main__':
    main()
