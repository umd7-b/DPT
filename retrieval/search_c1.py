"""C1-only gallery retrieval using pinned Chi-square; no fitting or new-image assumptions."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src import lbp236 as kernel
from features.C1_lbp.src.full_v04 import OUT, V04Context, FEATURE_VERSION, read_csv, write_json, save_csv


def rank_vectors(matrix, ids, query, *, query_id=None, top_k=5, epsilon=1e-8):
    """Ascending (distance, image_id); zero-distance duplicates remain eligible."""
    if type(top_k) is not int or top_k <= 0: raise ValueError('top_k must be positive integer')
    if epsilon != 1e-8: raise ValueError('Epsilon differs from versioned LBP spec')
    if (matrix.ndim != 2 or matrix.shape != (len(ids), 236) or matrix.dtype != np.float64
            or len(set(ids)) != len(ids) or not np.isfinite(matrix).all() or np.any(matrix < 0)):
        raise ValueError('Invalid gallery matrix or IDs')
    kernel.validate_vector(query)
    if not np.allclose(matrix.reshape(-1, 4, 59).sum(axis=2), 1., rtol=0, atol=1e-12):
        raise ValueError('Gallery requires per-region L1 histograms')
    distances = 0.5 * np.sum((matrix - query[None, :]) ** 2 / (matrix + query[None, :] + epsilon), axis=1)
    order = sorted((i for i, identity in enumerate(ids) if identity != query_id), key=lambda i: (float(distances[i]), ids[i]))
    return [(ids[i], float(distances[i])) for i in order[:top_k]]


class C1Gallery:
    def __init__(self, directory=OUT):
        self.directory = Path(directory); self.context = V04Context()
        self.manifest = json.loads((self.directory / 'manifest.json').read_text(encoding='utf-8'))
        self.context.require_lock(self.manifest)
        for filename, record in self.manifest['artifacts'].items():
            if Path(filename).name != filename or kernel.sha256(self.directory / filename) != record['sha256']:
                raise ValueError('Gallery artifact hash mismatch: ' + filename)
        self.schema = json.loads((self.directory / 'feature_schema.json').read_text(encoding='utf-8'))
        self.context.require_lock(self.schema)
        if (kernel.content_hash(self.schema) != self.schema['content_sha256']
                or self.schema['content_sha256'] != self.manifest['schema_content_sha256']
                or self.schema['distance']['epsilon'] != self.context.spec['conventions']['distance_epsilon']):
            raise ValueError('Feature schema/hash/epsilon mismatch')
        self.matrix = np.load(self.directory / 'features_C1.npy', allow_pickle=False)
        source_rows = read_csv(self.directory / 'feature_rows.csv')
        self.rows, self.by_id = sorted(source_rows, key=lambda r: int(r['feature_row_index'])), {}
        if self.matrix.shape != (len(self.rows), 236) or self.matrix.dtype != np.float64:
            raise ValueError('Feature matrix shape/dtype mismatch')
        for i, row in enumerate(self.rows):
            if (int(row['feature_row_index']) != i or row['image_id'] in self.by_id
                    or row['roi_contract_hash'] != self.context.lock['roi_contract_hash']
                    or row['lbp_spec_hash'] != self.context.lock['lbp_spec_hash'] or row['feature_version'] != FEATURE_VERSION):
                raise ValueError('Feature identity/version mapping mismatch')
            kernel.validate_vector(self.matrix[i]); self.by_id[row['image_id']] = row
        statuses = read_csv(self.directory / 'extraction_status.csv')
        if len(statuses) != self.manifest['processed_images'] or len({r['image_id'] for r in statuses}) != len(statuses):
            raise ValueError('Extraction status identity count mismatch')
        if {r['image_id'] for r in statuses if r['status'] == 'valid_C1'} != set(self.by_id):
            raise ValueError('Status/gallery identities differ')
        self.statuses = {r['image_id']: r for r in statuses}
        self.matrix.flags.writeable = False

    def resolve(self, image):
        path = Path(image); identity = path.stem
        if identity not in self.by_id:
            if identity in self.statuses: raise ValueError('Query missing_C1: ' + self.statuses[identity]['missing_reason'])
            raise ValueError('Gallery query only; new-image preprocessing/alignment is not implemented: ' + str(image))
        row = self.by_id[identity]
        if path.is_file() and kernel.sha256(path) != row['image_sha256']:
            raise ValueError('Provided query file differs from the gallery image')
        return identity

    def vector(self, identity):
        return self.matrix[int(self.by_id[identity]['feature_row_index'])].copy()

    def search(self, image, top_k=5):
        identity = self.resolve(image)
        ranking = rank_vectors(self.matrix, [r['image_id'] for r in self.rows], self.vector(identity),
                               query_id=identity, top_k=top_k, epsilon=self.schema['distance']['epsilon'])
        return identity, [dict(rank=i, **self.by_id[key], distance_C1=distance) for i, (key, distance) in enumerate(ranking, 1)]


def render(gallery, identity, results, path):
    entries = [('QUERY (excluded)', gallery.by_id[identity], None)] + [(f"#{r['rank']} Chi-square", r, r['distance_C1']) for r in results]
    width, height = 256, 316
    columns = min(3, len(entries)); rows = (len(entries) + columns - 1) // columns
    canvas = np.full((rows * height + 40, columns * width, 3), 250, np.uint8)
    cv2.putText(canvas, 'C1 ONLY / Chi-square 0.5 / ROI anatomy PROVISIONAL', (8, 25), 0, .48, (25, 25, 25), 1, cv2.LINE_AA)
    for i, (title, entry, distance) in enumerate(entries):
        if kernel.sha256(entry['image_path']) != entry['image_sha256']: raise ValueError('Image hash changed while rendering')
        image = cv2.imread(entry['image_path'], cv2.IMREAD_UNCHANGED)
        if image is None or image.shape != (256, 256, 3): raise ValueError('Unexpected source image')
        x, y = (i % columns) * width, 40 + (i // columns) * height
        canvas[y:y+256, x:x+256] = image
        cv2.putText(canvas, title, (x+7, y+274), 0, .44, (20, 20, 20), 1, cv2.LINE_AA)
        cv2.putText(canvas, entry['filename'], (x+7, y+291), 0, .4, (20, 20, 20), 1, cv2.LINE_AA)
        if distance is not None: cv2.putText(canvas, f'd={distance:.10f}', (x+7, y+309), 0, .4, (20, 20, 20), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(path), canvas): raise OSError('Cannot save comparison')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Gallery image_id, filename or matching file path')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--gallery', type=Path, default=OUT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    gallery = C1Gallery(args.gallery)
    identity, results = gallery.search(args.image, args.top_k)
    output = args.output or args.gallery / 'queries' / identity
    if output.exists(): raise FileExistsError('Query output exists; choose a new --output directory')
    output.mkdir(parents=True)
    fields = ['rank', 'image_id', 'filename', 'image_path', 'source', 'distance_C1', 'feature_row_index',
              'feature_version', 'roi_contract_hash', 'lbp_spec_hash']
    save_csv(output / 'results.csv', [{k: r[k] for k in fields} for r in results])
    write_json(output / 'results.json', dict(schema_id='C1_ONLY_GALLERY_QUERY_v1', **gallery.context.lock,
        query=gallery.by_id[identity], query_vector_sha256=hashlib.sha256(gallery.vector(identity).tobytes()).hexdigest(),
        metric=gallery.schema['distance'], self_excluded=True, sort='distance_C1 ascending, then image_id ascending',
        histograms_changed_by_query=False, new_image_support=False, results=results))
    render(gallery, identity, results, output / 'comparison.png')
    print('C1-only gallery query:', identity, '/ ROI anatomy PROVISIONAL')
    for row in results: print(row['rank'], row['filename'], f"Chi-square={row['distance_C1']:.12f}")
    print('Saved CSV, JSON, comparison:', output)


if __name__ == '__main__': main()
