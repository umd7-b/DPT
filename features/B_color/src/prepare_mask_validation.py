"""Audit dataset provenance and select a fixed, source-balanced 40-image panel."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import numpy as np

from features.B_color.src.mask_labels import DATASET, WORK, digest, read_csv, safe_destination, tile, write_csv, write_image

# Visual observations from the previous contact sheet, NOT semantic labels/GT.
ANCHORS = {
    'cfd_final_00001.png': 'long;dark;simple_background',
    'cfd_final_00069.png': 'short;dark;simple_background;smile',
    'cfd_final_00088.png': 'short_voluminous;dark;simple_background',
    'cfd_final_00103.png': 'long;dark;simple_background',
    'cfd_final_00205.png': 'short;light_brown;simple_background;smile',
    'cfd_final_00303.png': 'short;dark;simple_background',
    'cfd_final_00406.png': 'long;dark;simple_background',
    'cfd_final_00504.png': 'short;dark;simple_background',
    'cfd_final_00614.png': 'long;dark;simple_background;smile',
    'cfd_final_00716.png': 'long;light_brown;simple_background',
    'hf_merged_00051.png': 'short;light_brown;complex_background;glasses',
    'hf_merged_00146.png': 'short;dark;complex_background',
    'hf_merged_00241.png': 'short;dark;complex_background',
    'hf_merged_00336.png': 'long;dark;earrings',
    'hf_merged_00431.png': 'long;brown;complex_background;earrings',
    'hf_merged_00526.png': 'short;bangs;complex_background;secondary_person',
    'hf_merged_00621.png': 'long;brown;smile',
    'hf_merged_00716.png': 'long;dark;hat;complex_background',
    'hf_merged_00723.png': 'backlit;missing_skin_mask',
    'hf_merged_00728.png': 'light_blond;flower;complex_background;missing_skin_mask',
}


def descriptor(image):
    small = cv2.resize(image, (8, 8)).astype(np.float32).ravel() / 255
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [12, 4], [0, 180, 0, 256]).ravel()
    hist /= max(1, hist.sum())
    return np.r_[small / np.sqrt(small.size), hist]


def audit(dataset, output):
    metadata = read_csv(dataset / 'metadata.csv')
    groups = defaultdict(list)
    files = {p.name for p in (dataset / 'images').glob('*.png')}
    rows, features = [], {}
    for meta in metadata:
        name = meta['filename']
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Unsafe metadata filename')
        image_path = dataset / 'images' / name
        row = {'filename': name, 'source': meta['source'], 'review_note': meta.get('review_note', '')}
        problems = []
        if not image_path.exists():
            row['image_hash_matches'] = False
            problems.append('image_missing')
        else:
            row['image_hash_matches'] = digest(image_path) == meta['sha256']
            if not row['image_hash_matches']: problems.append('image_hash_mismatch')
            image = cv2.imread(str(image_path))
            if image is None:
                problems.append('image_unreadable')
            else:
                row['image_shape'] = str(image.shape)
                features[name] = descriptor(image)
        mask_path = dataset / 'skin_masks' / (Path(name).stem + '_skin.png')
        reference = meta.get('skin_mask_path', '')
        row['mask_reference_matches'] = reference.replace('\\', '/') == f'skin_masks/{mask_path.name}'
        if not mask_path.exists():
            row['mask_hash_matches'] = ''
            problems.append('mask_missing')
        else:
            row['mask_hash_matches'] = digest(mask_path) == meta.get('skin_mask_sha256', '')
            if not row['mask_hash_matches']: problems.append('mask_hash_mismatch')
            mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
            if mask is None:
                problems.append('mask_unreadable')
            else:
                row['mask_shape'] = str(mask.shape)
                row['binary_0_255'] = mask.dtype == np.uint8 and set(np.unique(mask)).issubset({0, 255})
                row['mask_pixels'] = int(np.count_nonzero(mask))
                key = __import__('hashlib').sha256(mask.tobytes()).hexdigest()
                row['decoded_sha256'] = key
                groups[key].append(name)
                if not row['binary_0_255']: problems.append('invalid_mask_values')
                if mask.shape != (256, 256): problems.append('invalid_mask_shape')
        row['issues'] = ';'.join(problems)
        rows.append(row)
    for row in rows:
        row['identical_mask_group_size'] = len(groups.get(row.get('decoded_sha256'), []))
        row['semantic_validity'] = 'unverified_repeated_template' if row['identical_mask_group_size'] > 1 else 'unverified'
    fields = ['filename','source','image_hash_matches','image_shape','mask_reference_matches',
              'mask_hash_matches','mask_shape','binary_0_255','mask_pixels','decoded_sha256',
              'identical_mask_group_size','semantic_validity','review_note','issues']
    write_csv(output / 'dataset_audit.csv', rows, fields)
    meta_names = [r['filename'] for r in metadata]
    provenance = read_csv(dataset / 'hf_provenance.csv')
    hashes = {r['filename']: r['sha256'] for r in metadata}
    prov_bad = [r['filename'] for r in provenance if hashes.get(r['filename']) != r['sha256']]
    actual_masks = {p.name for p in (dataset / 'skin_masks').glob('*.png')}
    expected_masks = {Path(n).stem + '_skin.png' for n in meta_names}
    summary = {
        'metadata_rows': len(metadata), 'sources': dict(Counter(r['source'] for r in metadata)),
        'duplicate_metadata_filenames': [n for n, c in Counter(meta_names).items() if c > 1],
        'orphan_images': sorted(files - set(meta_names)), 'orphan_skin_masks': sorted(actual_masks - expected_masks),
        'missing_skin_masks': [r['filename'] for r in rows if 'mask_missing' in r['issues']],
        'image_hash_mismatches': sum(r['image_hash_matches'] is False for r in rows),
        'mask_hash_mismatches': sum(r['mask_hash_matches'] is False for r in rows),
        'mask_reference_mismatches_when_present': sum(r['mask_reference_matches'] is False and 'mask_missing' not in r['issues'] for r in rows),
        'unique_decoded_masks': len(groups), 'identical_group_sizes': [len(v) for v in groups.values()],
        'hf_provenance_rows': len(provenance), 'hf_provenance_mismatches': prov_bad,
        'hf_missing_provenance': sorted(n for n in meta_names if n.startswith('hf_') and n not in {r['filename'] for r in provenance}),
        'documents': {n: digest(dataset / n) for n in ('README.md','description.txt','verification_report.json')},
        'generation_provenance': 'Not established by metadata or available dataset documentation. Hashes trace copies, not authoring method.',
        'missing_referenced_support': ['support_for_tasks_2_3_4_5/requirment.md','historical_metadata.zip'],
        'conclusion': 'Byte/hash integrity does not establish segmentation truth. Repeated masks are unverified spatial templates, never human GT.',
    }
    # Report local evidence only; do not infer how the masks were generated.
    summary['missing_referenced_support'] = [n for n in summary['missing_referenced_support'] if not (dataset / n).exists()]
    (output / 'audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return metadata, features


def select_panel(metadata, features):
    selected = [n for n in ANCHORS if n in features]
    # Fill 20 per source by farthest-point visual sampling, deterministically.
    for source in ('cfd', 'hf'):
        pool = sorted(r['filename'] for r in metadata if r['source'].lower() == source and r['filename'] in features)
        chosen = [n for n in selected if n in pool]
        if len(pool) < 20: raise ValueError(f'Not enough readable {source} images')
        if not chosen:
            chosen.append(pool[0])
            selected.append(pool[0])
        while len(chosen) < 20:
            remaining = [n for n in pool if n not in chosen]
            best = max(remaining, key=lambda n: min(float(np.linalg.norm(features[n]-features[c])) for c in chosen))
            chosen.append(best)
            selected.append(best)
    lookup = {r['filename']: r for r in metadata}
    return [{'filename': n, 'source': lookup[n]['source'], 'sha256': lookup[n]['sha256'],
             'selection': 'visual_anchor' if n in ANCHORS else 'farthest_point_color_spatial',
             'observed_tags': ANCHORS.get(n, 'unreviewed'), 'tags_user_verified': 'no',
             'dataset_review_note': lookup[n].get('review_note', ''),
             'split': 'development' if n in ANCHORS else 'held_out_do_not_tune'} for n in selected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DATASET)
    parser.add_argument('--output', type=Path, default=WORK)
    args = parser.parse_args()
    safe_destination(args.output, args.dataset)
    args.output.mkdir(parents=True, exist_ok=True)
    metadata, features = audit(args.dataset, args.output)
    panel = select_panel(metadata, features)
    write_csv(args.output / 'panel40.csv', panel, list(panel[0]))
    tiles = []
    for row in panel:
        image = cv2.imread(str(args.dataset / 'images' / row['filename']))
        tiles.append(tile(cv2.resize(image, (192, 192)), row['filename']))
    write_image(args.output / 'panel40_contact_sheet.png', np.vstack([np.hstack(tiles[i:i+5]) for i in range(0,40,5)]))
    print(f'Audited {len(metadata)} records; selected {len(panel)} images (20 CFD + 20 HF). No labels created.')


if __name__ == '__main__':
    main()
