"""Project-selected ROI v0.4 binding to the unchanged, pinned LBP236 kernel.

Selection for this implementation is not human anatomical certification.
The original spec/ROI dependency, trial context and old artifacts stay immutable.
"""
from pathlib import Path
from collections import Counter
import csv
import json
import sys

import cv2
import numpy as np

from . import lbp236 as kernel
from .trial100 import inputs, read_csv, write_json, ARCHIVE_HASH, KNOWN_VIOLATIONS

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/C1_lbp/full_v04'
ROI_PATH = ROOT / 'outputs/C1_lbp/roi_remediation_v0_4/candidate_contract_v0_4.json'
ROI_HASH = 'c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39'
KERNEL_HASH = 'c8793bbff26e871d3461c165a7e9d5168ebed7277905ff425edec2e8f2a888ff'
CODEBOOK_HASH = '7eb6a7a12b7374efb50d487f2e399b3475ef0e03594da35971bf083b0188ac94'
FEATURE_VERSION = 'C1_LBP236_FULL_ROI_V04_v1'


class V04Context(kernel.Context):
    def __init__(self, roi_path=ROI_PATH):
        if kernel.sha256(Path(kernel.__file__)) != KERNEL_HASH:
            raise ValueError('Validated kernel source hash changed')
        super().__init__()  # Authenticate the original spec, its v0.2 dependency and codebook.
        candidate = json.loads(Path(roi_path).read_text(encoding='utf-8'))
        if (candidate.get('schema_id') != 'C1_ROI_ANATOMICAL_CANDIDATE_v0.4.0'
                or candidate.get('content_sha256') != ROI_HASH or kernel.content_hash(candidate) != ROI_HASH):
            raise ValueError('ROI v0.4 schema/content hash mismatch')
        if self.lock['codebook_file_sha256'] != CODEBOOK_HASH:
            raise ValueError('Pinned codebook file changed')
        for name in kernel.REGIONS[1:]:
            if candidate['polygons'][name] != self.roi['polygons'][name]:
                raise ValueError('Unexpected change to unchanged ROI')
        if candidate['indices68_unchanged'] != self.roi['indices68_unchanged'] or candidate['region_order'] != list(kernel.REGIONS):
            raise ValueError('Mapping/order changed')
        self.roi = candidate
        self.lock = dict(feature_version=FEATURE_VERSION, roi_contract_hash=ROI_HASH, lbp_spec_hash=kernel.SPEC_HASH,
            codebook_file_sha256=CODEBOOK_HASH, kernel_source_sha256=KERNEL_HASH,
            implementation_binding='PROJECT_SELECTED_V04_SAME_LBP_SPEC_ARITHMETIC_v1', ROI_ANATOMY_STATUS='PROVISIONAL')


def protected_baseline():
    baseline = json.loads((OUT / 'evidence/baseline_before.json').read_text(encoding='utf-8'))
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or kernel.sha256(p) != h]
    if changed: raise ValueError('Protected artifacts changed: ' + repr(changed[:5]))
    return baseline


def save_csv(path, rows, fields=None):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def file_record(path):
    return dict(sha256=kernel.sha256(path), bytes=Path(path).stat().st_size)


def main():
    if (OUT / 'features_C1.npy').exists() or (OUT / 'image_diagnostics.jsonl').exists():
        raise FileExistsError('Full extraction already started/completed; no overwrite')
    baseline = protected_baseline()
    context = V04Context(); extractor = kernel.Extractor(context)
    images, landmarks = inputs()
    if len(images) != 1438 or set(images) != set(landmarks): raise ValueError('Image/landmark identity set mismatch')
    metrics = {(r['image_id'], r['region']): r for r in read_csv(ROOT / 'outputs/C1_lbp/roi_remediation_v0_4/roi_metrics.csv')
               if r['variant'] == 'candidate_v0_4'}
    schema = dict(schema_id='C1_LBP236_FULL_DATASET_SCHEMA_v1', **context.lock,
        logical_group='C', feature_name='C1', dimension=236, dtype='float64', count_dtype='uint64',
        region_order=list(kernel.REGIONS), region_bins=59, normalization='Independent L1 per59 bins; no global normalization/refit',
        distance=dict(name='Chi-square', coefficient=0.5, epsilon=context.spec['conventions']['distance_epsilon'],
                      formula='0.5*sum((a-b)^2/(a+b+epsilon))'),
        spec_binding=dict(original_spec_schema=context.spec['schema_id'], original_spec_content_hash=kernel.SPEC_HASH,
             original_spec_ROI_dependency=kernel.ROI_HASH, implementation_ROI=ROI_HASH,
             reason='Project owner explicitly selected ROI v0.4 for full dataset in current task; only ROI binding differs; arithmetic is reused unchanged.',
             anatomical_approval_claimed=False, old_spec_or_review_records_modified=False),
        ROI_file_sha256=kernel.sha256(ROI_PATH), landmark_archive_sha256=ARCHIVE_HASH,
        source_status='PROJECT_SELECTED_IMPLEMENTATION; ANATOMY_PROVISIONAL',
        project_selection=dict(source='User task: COMPLETE C1 LBP236 FOR THE FULL DATASET',
              instruction='Sử dụng ROI v0.4 làm phiên bản triển khai được chủ dự án lựa chọn cho nhiệm vụ này, không tuyên bố đã được chứng nhận chính xác giải phẫu.',
              date_local='2026-11-24', timezone='Asia/Saigon'),
        image_policy='Existing aligned256x256 uint8 BGR gallery images + authenticated pixel landmarks; no detector/alignment rerun',
        missing='Any invalid ROI or support<64 -> missing_C1; no vector/zero-fill',
        environment=dict(python=sys.version, numpy=np.__version__, opencv=cv2.__version__))
    schema['content_sha256'] = kernel.content_hash(schema)
    write_json(OUT / 'feature_schema.json', schema)
    rows, statuses, vectors, counts, eligible = [], [], [], [], []
    with (OUT / 'image_diagnostics.jsonl').open('x', encoding='utf-8', newline='\n') as diagnostics:
        for n, identity in enumerate(sorted(images), 1):
            image = images[identity]; archive_row, points = landmarks[identity]
            if Path(image['filename']).stem != identity or kernel.sha256(image['image_path']) != image['image_hash']:
                raise ValueError('Image identity/hash mismatch: ' + identity)
            bgr = cv2.imread(image['image_path'], cv2.IMREAD_UNCHANGED)
            try:
                result = extractor.extract(bgr, points, identity, image['source'])
            except ValueError as error:
                result = extractor._missing(identity, image['source'], 'extraction_value_error:' + str(error))
            row_index = None
            if result['status'] == 'valid_C1':
                for region in kernel.REGIONS:
                    measured, old = result['regions'][region], metrics[(identity, region)]
                    if (measured['raw_mask_sha256'] != old['raw_mask_sha256']
                            or measured['raw_mask_pixels'] != int(old['raw_mask_pixels'])
                            or measured['eligible_centres'] != int(old['eligible_centres'])):
                        raise ValueError('ROI/support differs from frozen v0.4 census: ' + identity + '/' + region)
                row_index = len(vectors)
                vectors.append(result['vector']); counts.append(result['counts'])
                eligible.append([result['regions'][r]['eligible_centres'] for r in kernel.REGIONS])
                rows.append(dict(feature_row_index=row_index, image_id=identity, filename=image['filename'],
                    image_path=image['image_path'], source=image['source'], image_sha256=image['image_hash'],
                    landmark_archive_row_index=archive_row, landmark_row_sha256=__import__('hashlib').sha256(points.tobytes()).hexdigest(),
                    feature_version=FEATURE_VERSION, dimension=236, dtype='float64',
                    roi_contract_hash=ROI_HASH, lbp_spec_hash=kernel.SPEC_HASH))
            status = dict(image_id=identity, filename=image['filename'], source=image['source'],
                status=result['status'], missing_reason=result['missing_reason'] or '',
                feature_row_index=row_index if row_index is not None else '', feature_version=FEATURE_VERSION,
                roi_contract_hash=ROI_HASH, lbp_spec_hash=kernel.SPEC_HASH,
                known_dataset_violation=KNOWN_VIOLATIONS.get(identity, ''), anatomical_status='PROVISIONAL')
            statuses.append(status)
            diagnostics.write(json.dumps(dict(status, regions=result['regions']), ensure_ascii=False, allow_nan=False) + '\n')
            if n % 100 == 0 or n == len(images): print('Processed', n, '/1438;', len(vectors), 'valid C1', flush=True)
    matrix = np.stack(vectors) if vectors else np.empty((0, 236), np.float64)
    arrays = {'features_C1.npy': matrix,
              'counts.npy': np.stack(counts) if counts else np.empty((0, 4, 59), np.uint64),
              'eligible_centres.npy': np.asarray(eligible, np.uint64).reshape(-1, 4)}
    for name, array in arrays.items():
        with (OUT / name).open('xb') as stream: np.save(stream, array, allow_pickle=False)
    save_csv(OUT / 'feature_rows.csv', rows, fields=['feature_row_index','image_id','filename','image_path','source','image_sha256',
        'landmark_archive_row_index','landmark_row_sha256','feature_version','dimension','dtype','roi_contract_hash','lbp_spec_hash'])
    save_csv(OUT / 'extraction_status.csv', statuses)
    artifacts = {name: file_record(OUT / name) for name in [*arrays, 'feature_rows.csv', 'extraction_status.csv',
                  'feature_schema.json', 'image_diagnostics.jsonl']}
    write_json(OUT / 'manifest.json', dict(schema_id='C1_FULL_V04_MANIFEST_v1', **context.lock,
        processed_images=len(statuses), valid_vectors=len(rows), missing_images=len(statuses) - len(rows),
        source_counts=dict(Counter(r['source'] for r in statuses)),
        valid_source_counts=dict(Counter(r['source'] for r in rows)),
        missing=[r for r in statuses if r['status'] != 'valid_C1'], artifacts=artifacts,
        schema_content_sha256=schema['content_sha256'], identity_order='image_id ascending; explicit feature_row_index, not source row position',
        protected_baseline_files=len(baseline), anatomy_status='PROVISIONAL', SQLite_writes=0,
        C2_or_fusion_implemented=False, detector_runs=0))
    print('Complete:', matrix.shape, 'missing:', len(statuses) - len(rows), flush=True)


if __name__ == '__main__': main()
