"""Frozen four-vector gallery and query-independent median calibration (PDF 2.5)."""
from pathlib import Path
import argparse
import math

import numpy as np

from retrieval import search_ab_v2 as ab
from retrieval.search_c1 import C1Gallery
from retrieval.search_c2 import C2Gallery
from shared.report_v2 import digest, read_json, read_csv, save_csv, write_json, pair_ids_digest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/retrieval/fusion_ab_c1_c2_v1'
POLICY_PATH = ROOT / 'retrieval/fusion_four_policy.json'
POLICY_SHA256 = '18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798'
SCHEMA_ID = 'FUSION_AB_C1_C2_MEDIAN_v1'
KINDS = ('a', 'b', 'c1', 'c2')
DIMENSIONS = dict(a=150, b=144, c1=236, c2=324)
EPSILON = EPSILON_C1 = 1e-8
WEIGHT_SUM_ATOL = 1e-12
MEDIAN_ATOL = MEDIAN_RTOL = 1e-12
AB_CALIBRATION = ab.OUT / 'calibration'


def policy():
    if digest(POLICY_PATH) != POLICY_SHA256:
        raise ValueError('Fusion policy hash mismatch')
    return read_json(POLICY_PATH)


def verify_inputs(fingerprint):
    for name, expected in fingerprint.items():
        if not Path(name).is_file() or digest(name) != expected:
            raise ValueError('Frozen input hash mismatch: ' + name)


def validate_weights(weights):
    values = np.asarray(weights, dtype=np.float64)
    if (values.shape != (4,) or not np.isfinite(values).all() or np.any(values < 0)
            or not math.isclose(math.fsum(values), 1., rel_tol=0., abs_tol=WEIGHT_SUM_ATOL)):
        raise ValueError('Four finite nonnegative weights must sum to 1 (absolute tolerance 1e-12); no renormalization')
    return values


def indexed_rows(rows, matrix, kind):
    """Metadata order is irrelevant; row indices locate vectors within EACH set."""
    if matrix.shape != (len(rows), DIMENSIONS[kind]) or matrix.dtype != np.float64 or not np.isfinite(matrix).all():
        raise ValueError('Feature shape/dtype/finite mismatch: ' + kind)
    field = 'a_row_index' if kind == 'a' else 'feature_row_index'
    by_id, used = {}, set()
    for row in rows:
        key, index = row['image_id'], int(row[field])
        if not key or key in by_id or index in used or index < 0 or index >= len(matrix):
            raise ValueError('Duplicate/invalid feature identity or index: ' + kind)
        by_id[key] = (index, row)
        used.add(index)
    return by_id


def join_by_id(sources):
    """No positional join across different features, including the 1437-row B."""
    maps = {kind: indexed_rows(*sources[kind], kind) for kind in KINDS}
    ids = sorted(set.intersection(*(set(m) for m in maps.values())))
    joined = {kind: np.array(sources[kind][1][[maps[kind][key][0] for key in ids]], copy=True)
              for kind in KINDS}
    for value in joined.values():
        value.flags.writeable = False
    return ids, joined, maps


def component_distances(left, right):
    """Broadcasting supports vector-vs-gallery and paired matrices."""
    result = {}
    for kind in KINDS:
        x, y = left[kind], right[kind]
        if kind == 'c1':
            value = .5 * np.sum((x-y)**2 / (x+y+EPSILON_C1), axis=-1)
        else:
            value = np.sqrt(np.sum((x-y)**2, axis=-1))
        if not np.isfinite(value).all() or np.any(value < 0):
            raise ValueError('Nonfinite/negative component distance')
        result[kind] = value
    return result


def combine(raw, params, weights):
    w = validate_weights(weights)
    normalized = {k: raw[k] / (params['medians'][k] + EPSILON) for k in KINDS}
    total = sum(w[i] * normalized[k] for i, k in enumerate(KINDS))
    return normalized, total


def rank_indices(ids, scores, query_id, top_k):
    if type(top_k) is not int or top_k <= 0:
        raise ValueError('top_k must be a positive integer')
    if len(set(ids)) != len(ids) or len(scores) != len(ids) or not np.isfinite(scores).all():
        raise ValueError('Invalid ranking IDs/scores')
    return sorted((i for i, key in enumerate(ids) if key != query_id),
                  key=lambda i: (float(scores[i]), ids[i]))[:top_k]


class FourGallery:
    def __init__(self):
        self.policy = policy()
        verify_inputs(self.policy['input_files'])
        # Existing loaders validate vector/stat/schema relationships without fitting.
        self.ab = ab.load_gallery()
        if not (AB_CALIBRATION/'median_params.json').is_file():
            raise ValueError('Frozen AB v2 calibration missing; regeneration prohibited')
        self.ab_params, reused = ab.calibrate(self.ab)
        if not reused:
            raise ValueError('AB calibration must only be reused')
        self.c1, self.c2 = C1Gallery(), C2Gallery()
        self.sources = dict(
            a=(self.ab.a_rows, self.ab.all_a),
            b=(read_csv(ab.b_v2.DEFAULT_OUTPUT/'feature_rows.csv'),
               np.load(ab.b_v2.DEFAULT_OUTPUT/'features_B_normalized.npy', allow_pickle=False)),
            c1=(self.c1.rows, self.c1.matrix), c2=(self.c2.rows, self.c2.matrix))
        self.ids, self.vectors, self.maps = join_by_id(self.sources)
        counts = {k: len(self.maps[k]) for k in KINDS}
        counts['intersection'] = len(self.ids)
        if counts != self.policy['expected_counts']:
            raise ValueError('Unexpected full gallery/intersection counts: ' + str(counts))
        if not (set(self.maps['a']) == set(self.maps['c1']) == set(self.maps['c2'])):
            raise ValueError('A/C1/C2 identity sets differ')
        missing_b = sorted(set(self.maps['a']) - set(self.maps['b']))
        if missing_b != self.policy['missing_b'] or set(self.maps['b'])-set(self.maps['a']):
            raise ValueError('Unexpected missing/extra B identities')
        if self.ids != self.ab_params['image_ids']:
            raise ValueError('Frozen AB v2 IDs differ from four-way intersection')
        self.by_id = {}
        for key in sorted(self.maps['a']):
            ar = self.maps['a'][key][1]
            c1r, c2r = self.maps['c1'][key][1], self.maps['c2'][key][1]
            if (c1r['filename'] != c2r['filename'] or ar['image_name'] != c1r['filename']
                    or Path(ar['image_path']).resolve() != Path(c1r['image_path']).resolve()
                    or Path(c1r['image_path']).resolve() != Path(c2r['image_path']).resolve()
                    or c1r['image_sha256'] != c2r['image_sha256'] or c1r['source'] != c2r['source']
                    or digest(ar['image_path']) != c1r['image_sha256']):
                raise ValueError('Image source/hash/mapping mismatch: ' + key)
            if key in self.maps['b']:
                br = self.maps['b'][key][1]
                if (br['source_sha256'] != c1r['image_sha256'] or br['image_name'] != c1r['filename']
                        or br['dataset_source'].casefold() != c1r['source'].casefold()
                        or int(br['a_row_index']) != self.maps['a'][key][0]):
                    raise ValueError('B source/image_id/a_row_index mismatch: ' + key)
            self.by_id[key] = dict(image_id=key, filename=c1r['filename'], source=c1r['source'],
                image_path=c1r['image_path'], image_sha256=c1r['image_sha256'],
                vector_rows={k: self.maps[k][key][0] if key in self.maps[k] else None for k in KINDS})
        self.positions = {key: i for i, key in enumerate(self.ids)}
        self.pairs = read_csv(AB_CALIBRATION/'representative_pairs.csv')
        self.pair_ids = [(r['image_id_1'], r['image_id_2']) for r in self.pairs]
        if (len(self.pair_ids) != self.policy['pair_count'] or len(set(self.pair_ids)) != len(self.pair_ids)
                or pair_ids_digest(self.pair_ids) != self.policy['pair_ids_sha256']
                or any(a >= b or a not in self.positions or b not in self.positions for a,b in self.pair_ids)):
            raise ValueError('Frozen 20,000 representative pair identities mismatch')

    def calibration_contract(self):
        return dict(schema_id=SCHEMA_ID, policy_sha256=POLICY_SHA256,
            feature_versions=self.policy['feature_versions'], fingerprint=self.policy['input_files'],
            image_ids=self.ids, pair_count=len(self.pair_ids), pair_ids_sha256=pair_ids_digest(self.pair_ids),
            epsilon=EPSILON, epsilon_c1=EPSILON_C1,
            ab_params_sha256=digest(AB_CALIBRATION/'median_params.json'),
            ab_pairs_sha256=digest(AB_CALIBRATION/'representative_pairs.csv'))

    def resolve(self, image):
        path = Path(image)
        if path.is_file():
            source_hash = digest(path)
            matches = sorted(k for k,r in self.by_id.items() if r['image_sha256'] == source_hash)
            if not matches:
                raise ValueError('Gallery image bytes only; new-image adapter unavailable')
            if path.stem in self.by_id:
                if path.stem not in matches:
                    raise ValueError('Query filename and source hash disagree')
                return path.stem
            if len(matches) != 1:
                raise ValueError('Ambiguous source hash; query by gallery image_id')
            return matches[0]
        if path.name != str(image):
            raise ValueError('Query path does not exist')
        if path.stem not in self.by_id:
            raise ValueError('Unknown gallery image_id/filename')
        if str(image) not in (path.stem,self.by_id[path.stem]['filename']):
            raise ValueError('Use the exact gallery image_id or filename')
        return path.stem


def build_calibration(gallery, directory=OUT/'calibration'):
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('Calibration exists; never regenerate or overwrite')
    indices = np.array([(gallery.positions[a],gallery.positions[b]) for a,b in gallery.pair_ids])
    raw = component_distances({k: gallery.vectors[k][indices[:,0]] for k in KINDS},
                              {k: gallery.vectors[k][indices[:,1]] for k in KINDS})
    medians = {k: float(np.median(raw[k])) for k in KINDS}
    for k in ('a','b'):
        if not math.isclose(medians[k], gallery.ab_params['median_'+k], rel_tol=MEDIAN_RTOL, abs_tol=MEDIAN_ATOL):
            raise ValueError('Recomputed median differs from frozen AB v2: ' + k)
    rows = [dict(pair_id=n, image_id_1=a, image_id_2=b,
                 **{'distance_'+k: float(raw[k][n]) for k in KINDS})
            for n,(a,b) in enumerate(gallery.pair_ids)]
    directory.mkdir(parents=True)
    save_csv(directory/'representative_pairs.csv', rows)
    params = dict(gallery.calibration_contract(), medians=medians,
        pairs_sha256=digest(directory/'representative_pairs.csv'), formula='d_k/(median_k+epsilon)',
        selection='Exact ordered 20000 AB v2 pairs; four distances recomputed; no query fitting',
        median_ab_tolerance=dict(atol=MEDIAN_ATOL,rtol=MEDIAN_RTOL))
    write_json(directory/'median_params.json', params)
    return params


def load_calibration(gallery, directory=OUT/'calibration'):
    directory = Path(directory)
    params = read_json(directory/'median_params.json')
    if any(params.get(k) != v for k,v in gallery.calibration_contract().items()):
        raise ValueError('Four-way calibration schema/version/fingerprint/ID mismatch')
    if digest(directory/'representative_pairs.csv') != params['pairs_sha256']:
        raise ValueError('Four-way pair CSV hash mismatch')
    rows = read_csv(directory/'representative_pairs.csv')
    if ([(r['image_id_1'],r['image_id_2']) for r in rows] != gallery.pair_ids
            or [int(r['pair_id']) for r in rows] != list(range(len(rows)))):
        raise ValueError('Four-way ordered pair IDs mismatch')
    for k in KINDS:
        values = np.array([float(r['distance_'+k]) for r in rows])
        median = params['medians'][k]
        if not np.isfinite(values).all() or np.any(values<0) or not math.isfinite(median) or median<0 or median != float(np.median(values)):
            raise ValueError('Saved four-way median disagrees with pair distances: '+k)
        if k in ('a','b') and not math.isclose(median,gallery.ab_params['median_'+k],rel_tol=MEDIAN_RTOL,abs_tol=MEDIAN_ATOL):
            raise ValueError('Saved median differs from AB v2')
    return params


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibrate',action='store_true',required=True)
    parser.parse_args()
    gallery=FourGallery()
    print(build_calibration(gallery)['medians'])


if __name__=='__main__':
    main()
