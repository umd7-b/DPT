"""Versioned human annotations. No predictions are imported into ground truth."""
import csv
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from shared.paths import PROJECT_ROOT

import cv2
import numpy as np

ROOT = PROJECT_ROOT
DATASET = Path(r'D:\TuNam4\dataset_HF_CFD_final')
WORK = ROOT / 'outputs/B_color/mask_validation'
LABELS = ROOT / 'annotations/manual_masks'
REGIONS = ('skin', 'hair')
PROTOCOL = 'visible-face-skin-scalp-hair-v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def image_names(manifest):
    names = [r['filename'] for r in read_csv(manifest)]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate filenames in manifest')
    for name in names:
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Manifest must contain image basenames')
    return names


def binary_mask(path, shape):
    mask = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if mask is None or mask.shape != shape or mask.dtype != np.uint8:
        raise ValueError(f'Unreadable/wrong shape/type mask: {path}')
    if not set(np.unique(mask)).issubset({0, 255}):
        raise ValueError(f'Mask is not binary 0/255: {path}')
    return mask


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f'Cannot write {path}')


def safe_destination(destination, *sources):
    dest = Path(destination).resolve()
    for source in sources:
        src = Path(source).resolve()
        if dest == src or src in dest.parents or dest in src.parents:
            raise ValueError(f'Output must not overlap protected inputs: {src}')


class Annotation:
    def __init__(self, image_path, label_root=LABELS):
        self.image_path = Path(image_path)
        self.image = cv2.imread(str(image_path))
        if self.image is None:
            raise ValueError(f'Unreadable image: {image_path}')
        self.source_hash = digest(image_path)
        self.directory = Path(label_root) / self.image_path.stem
        self.masks = {r: np.zeros(self.image.shape[:2], np.uint8) for r in REGIONS}
        self.review = {r: self.unreviewed() for r in REGIONS}
        self.history = []
        self.dirty = False
        pointer = self.directory / 'current.json'
        if pointer.exists():
            revision = json.loads(pointer.read_text(encoding='utf-8'))['revision']
            if Path(revision).name != revision or not revision.startswith('rev_'):
                raise ValueError('Invalid annotation revision')
            folder = self.directory / revision
            meta = json.loads((folder / 'annotation.json').read_text(encoding='utf-8'))
            if meta['source_sha256'] != self.source_hash or meta['protocol'] != PROTOCOL:
                raise ValueError('Annotation source/protocol mismatch')
            if meta['origin'] != 'human_drawn_from_blank':
                raise ValueError('Annotation origin is not independent human drawing')
            for r in REGIONS:
                mask_path = folder / f'{r}.png'
                if digest(mask_path) != meta['mask_sha256'][r]:
                    raise ValueError(f'Annotation mask hash mismatch: {r}')
                self.masks[r] = binary_mask(mask_path, self.image.shape[:2])
            if np.any((self.masks['skin'] > 0) & (self.masks['hair'] > 0)):
                raise ValueError('Overlapping human skin/hair annotations')
            review = meta['review']
            for r in REGIONS:
                item = review[r]
                if (not isinstance(item, dict) or type(item.get('confirmed')) is not bool
                        or type(item.get('empty_confirmed')) is not bool
                        or not isinstance(item.get('reviewer'), str)
                        or not isinstance(item.get('reviewed_at'), str)):
                    raise ValueError('Invalid annotation review metadata')
                if item['confirmed']:
                    datetime.fromisoformat(item['reviewed_at'])
                    if item['empty_confirmed'] and np.any(self.masks[r]):
                        raise ValueError('Absence confirmation conflicts with nonempty mask')
            self.review = review

    @staticmethod
    def unreviewed():
        return {'confirmed': False, 'reviewer': '', 'reviewed_at': '', 'empty_confirmed': False}

    def checkpoint(self):
        self.history.append(({r: m.copy() for r, m in self.masks.items()},
                             json.loads(json.dumps(self.review))))
        self.history = self.history[-60:]

    def paint(self, region, start, end, radius, erase=False, new_stroke=True):
        if new_stroke:
            self.checkpoint()
        cv2.line(self.masks[region], start, end, 0 if erase else 255, radius * 2 + 1)
        self.review[region] = self.unreviewed()
        if not erase:
            other = next(r for r in REGIONS if r != region)
            overlap = (self.masks[region] > 0) & (self.masks[other] > 0)
            if np.any(overlap):
                self.masks[other][overlap] = 0
                self.review[other] = self.unreviewed()
        self.dirty = True

    def undo(self):
        if self.history:
            self.masks, self.review = self.history.pop()
            self.dirty = True

    def clear(self, region):
        self.checkpoint()
        self.masks[region][:] = 0
        self.review[region] = self.unreviewed()
        self.dirty = True

    def confirm(self, region, reviewer, empty_confirmed=False):
        if not reviewer.strip():
            raise ValueError('A named human reviewer is required')
        if not np.any(self.masks[region]) and not empty_confirmed:
            raise ValueError('Empty region requires explicit absence confirmation')
        self.checkpoint()
        self.review[region] = {'confirmed': True, 'reviewer': reviewer.strip(),
                               'reviewed_at': datetime.now(timezone.utc).isoformat(),
                               'empty_confirmed': bool(empty_confirmed)}
        self.dirty = True

    def save(self, annotator):
        if not annotator.strip():
            raise ValueError('Annotator name required')
        if digest(self.image_path) != self.source_hash:
            raise ValueError('Source changed while annotating')
        revision = 'rev_' + uuid.uuid4().hex
        folder = self.directory / revision
        folder.mkdir(parents=True)
        for r, mask in self.masks.items():
            write_image(folder / f'{r}.png', mask)
        meta = {'source_filename': self.image_path.name, 'source_sha256': self.source_hash,
                'shape': list(self.image.shape[:2]), 'protocol': PROTOCOL,
                'origin': 'human_drawn_from_blank', 'annotator': annotator.strip(),
                'saved_at': datetime.now(timezone.utc).isoformat(), 'review': self.review,
                'mask_sha256': {r: digest(folder / f'{r}.png') for r in REGIONS}}
        (folder / 'annotation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        temporary = self.directory / f'.pointer_{uuid.uuid4().hex}.json'
        temporary.write_text(json.dumps({'revision': revision}), encoding='utf-8')
        os.replace(temporary, self.directory / 'current.json')
        self.dirty = False

    def valid_region(self, region):
        review = self.review[region]
        if review.get('confirmed') is not True or not review.get('reviewer', '').strip() or not review.get('reviewed_at'):
            return False
        return bool(np.any(self.masks[region])) or review.get('empty_confirmed') is True


def overlay(image, mask, color):
    result = image.copy()
    result[mask > 0] = (result[mask > 0] * .55 + np.array(color) * .45).astype(np.uint8)
    return result


def tile(image, title):
    result = cv2.copyMakeBorder(image, 26, 0, 0, 0, cv2.BORDER_CONSTANT, value=(30, 30, 30))
    cv2.putText(result, title, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
    return result
