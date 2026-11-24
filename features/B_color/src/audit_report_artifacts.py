"""Read-only checks of saved B trial artifacts; no extraction or ranking writes.

Numerical agreement cannot confirm report details that the report leaves open.
Run from the project root with the existing .venv-uniface environment.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATASET = Path('D:/TuNam4/dataset_HF_CFD_final')
VARIANTS = ('A_skin1_hair17_raw', 'B_skin1_hair17_clean', 'C_skin1or10_hair17_raw')
LABELS = ('Raw', 'Clean', 'Skin + Nose')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def verify_manifest(directory):
    rows = read_csv(directory/'artifact_manifest.csv')
    for row in rows:
        path = (directory/row['path']).resolve()
        if directory not in path.parents:
            raise ValueError('Manifest path escapes input directory')
        if sha256(path) != row['sha256']:
            raise ValueError(f'Artifact changed: {path}')
    return len(rows)


def load_binary(path):
    mask = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if mask is None or mask.shape != (256, 256) or mask.dtype != np.uint8:
        raise ValueError(f'Invalid mask dimensions/type: {path}')
    if not set(np.unique(mask)).issubset({0, 255}):
        raise ValueError(f'Nonbinary mask: {path}')
    return mask


def independent_erosion(mask):
    # Intersection of nine translated neighborhoods. Outside-image pixels are
    # neutral for erosion, matching the current OpenCV default border convention.
    padded = np.pad(mask == 255, 1, constant_values=True)
    keep = np.ones(mask.shape, dtype=bool)
    for y in range(3):
        for x in range(3):
            keep &= padded[y:y+256, x:x+256]
    return keep.astype(np.uint8)*255


def run(trial, evaluation, output):
    trial, evaluation, output = (Path(p).resolve() for p in (trial, evaluation, output))
    base = (ROOT/'outputs/B_color').resolve()
    uniface = base/'uniface_full'
    for protected in (trial, evaluation, uniface, DATASET.resolve(), base/'uniface_batch_100',
                      (ROOT/'outputs/A_geometry').resolve()):
        if output == protected or protected in output.parents or output in protected.parents:
            raise ValueError('Output overlaps protected input')
    if base not in output.parents or (output.exists() and any(output.iterdir())):
        raise ValueError('Use a new/empty B_color audit output directory')
    counts = {'trial_manifest_files': verify_manifest(trial),
              'evaluation_manifest_files': verify_manifest(evaluation)}
    summary = json.loads((trial/'summary.json').read_text(encoding='utf-8'))
    if summary['normalization_profile'] != 'all144':
        raise ValueError('This audit expects the existing user-confirmed all144 trial')
    a_rows = read_csv(ROOT/'outputs/A_geometry/features/metadata.csv')
    sample = read_csv(base/'uniface_batch_100/manifest.csv')
    sample_names = {r['image_name'] for r in sample}
    if len(sample) != 100 or len(sample_names) != 100:
        raise ValueError('Expected the original 100-image sample')
    expected_order = [(i,r['image_name']) for i,r in enumerate(a_rows) if r['image_name'] in sample_names]
    matrices, names_by_label, normalization = {}, {}, []
    hist_checks = 0
    for variant, label in zip(VARIANTS, LABELS):
        directory = trial/variant
        x = np.load(directory/'features_B_unscaled.npy', allow_pickle=False)
        z = np.load(directory/'features_B_normalized.npy', allow_pickle=False)
        rows = read_csv(directory/'feature_rows.csv')
        if x.shape != (100,144) or z.shape != (100,144) or not np.isfinite(x).all() or not np.isfinite(z).all():
            raise ValueError(f'Invalid existing vectors: {variant}')
        if [(int(r['a_row_index']),r['image_name']) for r in rows] != expected_order:
            raise ValueError('Trial not in original sample/A metadata order')
        names = [r['image_name'] for r in rows]
        for start, stop in ((0,48),(60,70),(72,120),(132,142)):
            for histogram in x[:,start:stop]:
                if min(histogram) < 0 or not math.isclose(math.fsum(histogram),1,abs_tol=1e-12):
                    raise ValueError('Saved histogram does not have L1 sum 1')
                hist_checks += 1
        if np.any(x[:,[70,71,142,143]] < 0) or np.any(x[:,[70,71,142,143]] > 1):
            raise ValueError('Saved circular statistics outside [0,1]')
        # Independent scalar summation; no fit_standardizer/transform calls.
        means = np.array([math.fsum(float(v) for v in column)/100 for column in x.T])
        raw_std = np.array([math.sqrt(math.fsum((float(v)-mu)**2 for v in column)/100)
                            for column,mu in zip(x.T,means)])
        divisors = np.array([1. if value < 1e-8 else value for value in raw_std])
        with np.load(directory/'normalization_stats.npz',allow_pickle=False) as saved:
            sm, ss = saved['mean'].copy(), saved['std'].copy()
            np.testing.assert_allclose(sm, means, atol=1e-11, rtol=1e-12)
            np.testing.assert_allclose(ss, divisors, atol=1e-11, rtol=1e-12)
            np.testing.assert_array_equal(saved['constant_dimensions'], np.flatnonzero(raw_std<1e-8))
        independently_normalized = (x-means)/divisors
        np.testing.assert_allclose(z, independently_normalized, atol=1e-10, rtol=1e-10)
        np.testing.assert_array_equal(z, (x-sm)/ss)
        normalization.append({'variant':variant, 'vectors':len(x),
                              'zero_variance_dimensions':int(np.sum(raw_std == 0)),
                              'below_1e_minus_8_threshold_dimensions':int(np.sum(raw_std < 1e-8)),
                              'max_independent_mean_error':float(np.max(np.abs(means-sm))),
                              'max_independent_std_error':float(np.max(np.abs(divisors-ss))),
                              'max_independent_z_error':float(np.max(np.abs(independently_normalized-z))),
                              'saved_formula_reconstruction_error':float(np.max(np.abs(z-(x-sm)/ss)))})
        matrices[label] = z; names_by_label[label] = names
    if any(names != names_by_label['Raw'] for names in names_by_label.values()):
        raise ValueError('Variant name/order mismatch')
    image_rows = read_csv(trial/VARIANTS[0]/'feature_rows.csv')
    masks_checked = clean_checks = 0
    for row in image_rows:
        name, stem = row['image_name'], Path(row['image_name']).stem
        if sha256(DATASET/'images'/name) != row['source_sha256']:
            raise ValueError('Source image hash mismatch')
        labels = cv2.imread(str(trial/VARIANTS[2]/'class_maps'/name),cv2.IMREAD_UNCHANGED)
        if labels is None or labels.shape != (256,256) or labels.dtype != np.uint8 or labels.max()>18:
            raise ValueError('Invalid existing class map')
        for region, class_id in (('skin',1),('hair',17)):
            original = load_binary(uniface/'masks'/region/f'{stem}_{region}_mask.png')
            clean = load_binary(uniface/'masks'/f'{region}_clean'/f'{stem}_{region}_clean_mask.png')
            experimental = load_binary(trial/VARIANTS[2]/'masks'/region/f'{stem}_{region}_mask.png')
            np.testing.assert_array_equal(original,(labels==class_id).astype(np.uint8)*255)
            selected = ((labels==1)|(labels==10)) if region=='skin' else (labels==17)
            np.testing.assert_array_equal(experimental,selected.astype(np.uint8)*255)
            np.testing.assert_array_equal(clean,independent_erosion(original))
            masks_checked += 3; clean_checks += 1
    # Validate existing rankings independently, without writing/replacing any
    # ranking or using the production top5 helper.
    rankings = read_csv(evaluation/'top5_long.csv')
    if len(rankings) != 150:
        raise ValueError('Expected 10 x 3 x 5 saved result rows')
    distance_error = 0.
    for row in rankings:
        z, names = matrices[row['variant']], names_by_label[row['variant']]
        query = names.index(row['query'])
        distances = [(math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(z[query],z[i]))),name)
                     for i,name in enumerate(names) if name != row['query']]
        expected_distance, expected_name = sorted(distances)[int(row['rank'])-1]
        if row['image_name'] != expected_name or row['image_name'] == row['query']:
            raise ValueError('Existing saved Euclidean ranking mismatch')
        error = abs(expected_distance-float(row['distance']))
        if error > 1e-10:raise ValueError('Existing saved Euclidean distance mismatch')
        distance_error = max(distance_error,error)
    counts.update(gallery_vectors=300, histograms_checked=hist_checks, source_images_verified=100,
                  masks_format_verified=masks_checked, class_maps_verified=100,
                  erosion_checks=clean_checks, saved_ranking_rows_verified=len(rankings),
                  max_independent_distance_error=distance_error, normalization=normalization,
                  new_inferences=0, new_features_persisted=0, ranking_files_written=0,
                  official_configuration=None,
                  academic_status='Partial verification only; unspecified report details need group confirmation')
    output.mkdir(parents=True,exist_ok=True)
    (output/'artifact_validation.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',type=Path,default=ROOT/'outputs/B_color/color_features_100')
    parser.add_argument('--evaluation',type=Path,default=ROOT/'outputs/B_color/color_evaluation_10')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/B_color/report_compliance_audit/artifact_checks')
    args = parser.parse_args()
    print(json.dumps(run(args.trial,args.evaluation,args.output),indent=2))


if __name__ == '__main__':
    main()
