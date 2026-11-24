"""UniFace batch/full dataset parsing using existing local weights only.

Run: python -m features.B_color.src.batch_uniface
Masks are predictions, never human ground truth. No color vectors are extracted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
from importlib.metadata import version
import json
import logging
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch
from urllib.parse import urlparse

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET = Path(r'D:\TuNam4\dataset_HF_CFD_final')
DEFAULT_OUTPUT = PROJECT_ROOT / 'outputs/B_color/uniface_batch_100'
FIELDS = ['image_name', 'dataset_source', 'skin_pixels', 'hair_pixels',
          'skin_clean_pixels', 'hair_clean_pixels', 'skin_area_ratio', 'hair_area_ratio',
          'erosion_skin_loss_ratio', 'erosion_hair_loss_ratio', 'processing_time_ms',
          'warning', 'status', 'reason', 'skin_clean_area_ratio', 'hair_clean_area_ratio',
          'skin_components', 'hair_components', 'skin_border_pixels', 'hair_side_bottom_border_pixels',
          'dataset_review_note', 'face_count_check', 'skin_clean_components', 'hair_clean_components']
# Screening thresholds, not calibrated probabilities or measured quality.
THRESHOLDS = {'skin_min_area_ratio': .03, 'skin_max_area_ratio': .60,
              'hair_min_area_ratio': .003, 'hair_max_area_ratio': .60,
              'erosion_max_loss_ratio': .35, 'max_significant_components': 8,
              'component_min_area_ratio': .0005, 'skin_border_pixels': 20,
              'hair_side_bottom_border_pixels': 20}
LOG = logging.getLogger('uniface_batch')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def write_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise OSError(f'Cannot save {path}')


def select_images(image_dir, seed=42):
    """Sorted pools + local RNG; filesystem enumeration cannot affect selection."""
    rng = random.Random(seed)
    selected = {}
    for source, prefix in [('CFD', 'cfd_final_'), ('HF', 'hf_merged_')]:
        pool = sorted(p for p in Path(image_dir).glob(prefix + '*.png') if p.is_file())
        if len(pool) < 50:
            raise ValueError(f'{source}: need at least 50 images; found {len(pool)}. No cross-source replacement.')
        selected[source] = rng.sample(pool, 50)
    # Each 20-image contact page has 10 CFD + 10 HF, in manifest order.
    return [(p, source) for pair in zip(selected['CFD'], selected['HF'])
            for p, source in zip(pair, ('CFD', 'HF'))]


def create_parser():
    """Use only verified local weights. Inference implementation is unchanged."""
    from uniface.constants import MODEL_REGISTRY, ParsingWeights
    from uniface.model_store import get_cache_dir
    from uniface.parsing import BiSeNet
    weights = ParsingWeights.RESNET18  # Same default as test_uniface.py.
    info = MODEL_REGISTRY[weights]
    model_path = Path(get_cache_dir()) / (weights.value + Path(urlparse(info.url).path).suffix)
    if not model_path.is_file():
        raise FileNotFoundError(f'Existing UniFace weights required: {model_path}. Downloads disabled.')
    model_hash = sha256(model_path)
    if model_hash != info.sha256:
        raise ValueError('Cached UniFace model SHA-256 mismatch. Refusing download or replacement.')
    # The package resolver can download/delete cache files. Replace only this
    # resolver during initialization with the verified local filename, never parse.
    with patch('uniface.parsing.bisenet.verify_model_weights', return_value=str(model_path)):
        parser = BiSeNet()
    return parser, {'model_path': str(model_path), 'model_sha256': model_hash,
                    'model': weights.value, 'uniface_version': version('uniface'),
                    'providers': parser.session.get_providers()}


def make_masks(labels, shape=(256, 256)):
    labels = np.asarray(labels)
    if labels.shape != shape or labels.dtype.kind not in 'iu':
        raise ValueError(f'Invalid parser label shape/type: {labels.shape}, {labels.dtype}')
    if np.any((labels < 0) | (labels > 18)):
        raise ValueError('Unexpected parser class IDs outside [0,18]')
    skin = (labels == 1).astype(np.uint8) * 255
    hair = (labels == 17).astype(np.uint8) * 255
    kernel = np.ones((3, 3), np.uint8)
    masks = {'skin': skin, 'hair': hair,
             'skin_clean': cv2.erode(skin, kernel, iterations=1),
             'hair_clean': cv2.erode(hair, kernel, iterations=1)}
    for name, mask in masks.items():
        if mask.shape != (256, 256) or mask.dtype != np.uint8 or not set(np.unique(mask)).issubset({0, 255}):
            raise ValueError(f'Invalid binary mask: {name}')
    return masks


def quality(masks):
    numbers = {f'{r}_pixels': int(np.count_nonzero(m)) for r, m in masks.items()}
    flags = {r: [] for r in masks}
    for region in ('skin', 'hair'):
        mask = masks[region]
        pixels = numbers[f'{region}_pixels']
        clean_pixels = numbers[f'{region}_clean_pixels']
        area = pixels / mask.size
        numbers[f'{region}_area_ratio'] = area
        numbers[f'{region}_clean_area_ratio'] = clean_pixels / mask.size
        loss = (pixels - clean_pixels) / pixels if pixels else ''
        numbers[f'erosion_{region}_loss_ratio'] = loss
        if pixels == 0:
            flags[region].append('empty')
        elif area < THRESHOLDS[f'{region}_min_area_ratio']:
            flags[region].append('small_area')
        elif area > THRESHOLDS[f'{region}_max_area_ratio']:
            flags[region].append('large_area')
        if clean_pixels == 0:
            flags[region+'_clean'].append('empty')
        elif clean_pixels / mask.size < THRESHOLDS[f'{region}_min_area_ratio']:
            flags[region+'_clean'].append('small_area')
        elif clean_pixels / mask.size > THRESHOLDS[f'{region}_max_area_ratio']:
            flags[region+'_clean'].append('large_area')
        _, _, clean_stats, _ = cv2.connectedComponentsWithStats(masks[region+'_clean'], connectivity=8)
        clean_components = int(np.sum(clean_stats[1:, cv2.CC_STAT_AREA] >= max(8,int(mask.size*THRESHOLDS['component_min_area_ratio']))))
        numbers[f'{region}_clean_components'] = clean_components
        if clean_components > THRESHOLDS['max_significant_components']:
            flags[region+'_clean'].append('fragmented')
        if loss != '' and loss > THRESHOLDS['erosion_max_loss_ratio']:
            flags[region+'_clean'].append('large_erosion_loss')
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        components = int(np.sum(stats[1:, cv2.CC_STAT_AREA] >= max(8, int(mask.size*THRESHOLDS['component_min_area_ratio']))))
        numbers[f'{region}_components'] = components
        if components > THRESHOLDS['max_significant_components']:
            flags[region].append('fragmented')
    skin = masks['skin']
    border = np.zeros_like(skin, dtype=bool)
    border[[0,-1],:] = True; border[:,[0,-1]] = True
    numbers['skin_border_pixels'] = int(np.count_nonzero((skin>0)&border))
    if numbers['skin_border_pixels'] > THRESHOLDS['skin_border_pixels']:
        flags['skin'].append('touches_image_border')
    hair_border = border.copy(); hair_border[0,1:-1] = False
    numbers['hair_side_bottom_border_pixels'] = int(np.count_nonzero((masks['hair']>0)&hair_border))
    if numbers['hair_side_bottom_border_pixels'] > THRESHOLDS['hair_side_bottom_border_pixels']:
        flags['hair'].append('side_or_bottom_crop_review')
    numbers['warning'] = ';'.join(f'{r}:{flag}' for r in masks for flag in flags[r])
    return numbers, flags


def preview(image, masks):
    tiles = [image] + [cv2.bitwise_and(image, image, mask=masks[r])
                      for r in ('skin', 'skin_clean', 'hair', 'hair_clean')]
    result = []
    for tile, title in zip(tiles, ('Original', 'Skin raw', 'Skin clean', 'Hair raw', 'Hair clean')):
        panel = cv2.copyMakeBorder(tile, 26, 0, 0, 0, cv2.BORDER_CONSTANT, value=(30,30,30))
        cv2.putText(panel, title, (6,18), cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1,cv2.LINE_AA)
        result.append(panel)
    return np.hstack(result)


def protected_hashes(dataset):
    # Read-only audit over originals. No segmentation of unselected images.
    return {p.relative_to(dataset).as_posix(): sha256(p)
            for folder in ('images', 'skin_masks')
            for p in sorted((dataset/folder).glob('*')) if p.is_file()}


def select_all_images(image_dir):
    selected = []
    for source, prefix in [('CFD', 'cfd_final_'), ('HF', 'hf_merged_')]:
        pool = sorted(p for p in Path(image_dir).glob(prefix+'*.png') if p.is_file())
        if not pool:
            raise ValueError(f'No {source} images found')
        selected.extend((p, source) for p in pool)
    actual = {p.name for p in Path(image_dir).glob('*.png') if p.is_file()}
    if actual != {p.name for p, _ in selected}:
        raise ValueError('Unknown image prefix: full mode requires CFD/HF PNG images')
    return selected


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def atomic_json(path, data):
    temporary = path.with_name('.'+path.name+'.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(path)


def write_once(path, data):
    """Never replace an existing prediction, even if a previous attempt crashed."""
    try:
        with path.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError(f'Existing artifact differs; refused overwrite: {path}')


def output_masks(output, name):
    stem = Path(name).stem
    return {r: output/'masks'/r/f'{stem}_{r}_mask.png'
            for r in ('skin','hair','skin_clean','hair_clean')}


def load_receipt(output, name, source_hash):
    path = output/'receipts'/f'{Path(name).stem}.json'
    if not path.exists():
        return None
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt['source_sha256'] != source_hash or receipt['row']['image_name'] != name:
        raise ValueError('Receipt input fingerprint mismatch')
    expected = list(output_masks(output, name).values())+[output/'previews'/f'{Path(name).stem}_preview.png']
    if set(receipt['artifacts']) != {p.relative_to(output).as_posix() for p in expected}:
        raise ValueError('Receipt artifact list mismatch')
    for artifact in expected:
        if not artifact.is_file() or sha256(artifact) != receipt['artifacts'][artifact.relative_to(output).as_posix()]:
            raise ValueError(f'Artifact integrity mismatch: {artifact.name}; not overwritten')
    return receipt


def dataset_notes(dataset):
    notes = {}
    path = dataset/'review_candidates.csv'
    if path.is_file():
        for row in read_csv(path):
            notes[row['filename']] = row.get('reason','')
    return notes


def save_contact_pages(rows, output, split_sources):
    pages = []
    groups = [(s, [r for r in rows if r['dataset_source']==s]) for s in ('CFD','HF')] if split_sources else [('',rows)]
    for source, group in groups:
        directory = output/'contact_sheet'/source if source else output/'contact_sheet'
        directory.mkdir(parents=True, exist_ok=True)
        for offset in range(0,len(group),20):
            tiles = []
            for row in group[offset:offset+20]:
                p = output/'previews'/f'{Path(row["image_name"]).stem}_preview.png'
                panel = cv2.imread(str(p)) if row['status']=='success' else None
                if panel is None: panel = np.full((282,1280,3),35,np.uint8)
                tile = cv2.copyMakeBorder(panel,32,0,0,0,cv2.BORDER_CONSTANT,value=(30,30,30))
                caption = f'{row["image_name"]} [{row["dataset_source"]}] {row["status"]}'
                cv2.putText(tile,caption,(8,23),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1,cv2.LINE_AA)
                if row['warning']: cv2.circle(tile,(tile.shape[1]-20,15),7,(0,160,255),-1)
                tiles.append(tile)
            if len(tiles)%2: tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack([np.hstack(tiles[i:i+2]) for i in range(0,len(tiles),2)])
            path = directory/f'page_{offset//20+1:02d}.png'
            write_image(path,sheet)
            pages.append({'path':path.relative_to(output).as_posix(), 'source':source or 'mixed',
                          'images':[r['image_name'] for r in group[offset:offset+20]]})
    atomic_json(output/'contact_sheet/index.json',pages)
    return pages


def validate_outputs(selected, output, originals, rows):
    errors, checks, valid = [], [], 0
    expected_files = set()
    for (path, source), row in zip(selected,rows):
        if row['status'] != 'success':
            continue
        try:
            if load_receipt(output,path.name,originals.get('images/'+path.name,'')) is None:
                raise ValueError('Missing receipt')
            masks = {}
            for region, mask_path in output_masks(output,path.name).items():
                expected_files.add(mask_path.resolve())
                mask = cv2.imread(str(mask_path),cv2.IMREAD_UNCHANGED)
                if mask is None or mask.shape!=(256,256) or mask.dtype!=np.uint8 or not set(np.unique(mask)).issubset({0,255}):
                    raise ValueError(f'Invalid mask shape/type/values: {region}')
                if np.count_nonzero(mask)!=int(row[f'{region}_pixels']):
                    raise ValueError(f'Mask pixel count mismatch: {region}')
                masks[region]=mask
            for region in ('skin','hair'):
                if not np.array_equal(masks[region+'_clean'],cv2.erode(masks[region],np.ones((3,3),np.uint8),iterations=1)):
                    raise ValueError(f'Erosion mismatch: {region}')
            if np.any((masks['skin']>0)&(masks['hair']>0)):
                raise ValueError('Skin/hair overlap')
            valid += 4
            checks.append({'image_name':path.name,'dataset_source':source,'format_status':'valid',
                           'valid_masks':4,'source_sha256':originals.get('images/'+path.name,'')})
        except (OSError,ValueError,KeyError,TypeError) as error:
            errors.append({'image_name':path.name,'reason':str(error)})
    actual = {p.resolve() for p in (output/'masks').glob('*/*.png')}
    unexpected = sorted(str(p.relative_to(output)) for p in actual-expected_files)
    write_csv(output/'validation.csv',checks,['image_name','dataset_source','format_status','valid_masks','source_sha256'])
    return {'valid_masks':valid,'expected_masks_for_success':4*sum(r['status']=='success' for r in rows),
            'total_masks_on_disk':len(actual),'expected_masks_for_selection':len(selected)*4,
            'errors':errors,'unexpected_or_partial_mask_files':unexpected,
            'unique_selected_names':len({p.name for p,_ in selected}),
            'metrics_rows':len(rows),'all_success_names_have_valid_receipts':not errors}


def run_batch(selected, dataset, output, parser_factory=create_parser, seed=42,
              resume=False, split_sources=False):
    started = time.perf_counter()
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    if not selected or len({p.name for p,_ in selected}) != len(selected):
        raise ValueError('Selection must be nonempty with unique image names')
    if output == dataset or dataset in output.parents or output in dataset.parents:
        raise ValueError('Output directory must not overlap dataset')
    if output.exists() and any(output.iterdir()) and not resume:
        raise FileExistsError(f'Output is not empty: {output}. Use --retry-failed or a new directory.')
    originals = protected_hashes(dataset)
    selected_pairs = [(p.name,s) for p,s in selected]
    code_hash = sha256(Path(__file__))
    metadata_hashes = {name:sha256(dataset/name) for name in ('metadata.csv','review_candidates.csv') if (dataset/name).is_file()}
    if resume:
        if not (output/'run_config.json').is_file():
            raise ValueError('Cannot resume: missing run_config.json')
        config = json.loads((output/'run_config.json').read_text())
        existing = read_csv(output/'manifest.csv')
        if selected_pairs != [(r['image_name'],r['dataset_source']) for r in existing]:
            raise ValueError('Selection differs from original run; use a new output directory')
        if config['dataset'] != str(dataset) or config['script_sha256'] != code_hash:
            raise ValueError('Dataset path/script differs from original run')
        if config['thresholds'] != THRESHOLDS or config['split_sources'] != split_sources or config['seed'] != seed or config['metadata_hashes'] != metadata_hashes:
            raise ValueError('Run configuration differs from original run')
        saved_inputs = json.loads((output/'input_hashes.json').read_text())
        if originals != saved_inputs:
            raise ValueError('Original inputs changed since initial run; use a new output directory')
        model_info = config['model']
    output.mkdir(parents=True, exist_ok=True)
    for folder in ('masks/skin','masks/hair','masks/skin_clean','masks/hair_clean','previews','contact_sheet','receipts','attempts'):
        (output/folder).mkdir(parents=True, exist_ok=True)
    attempt = output/'attempts'/str(time.time_ns())
    attempt.mkdir()
    for name in ('metrics.csv','failed_images.csv','summary.json'):
        if (output/name).exists():
            (attempt/('previous_'+name)).write_bytes((output/name).read_bytes())
    notes = dataset_notes(dataset)
    if not resume:
        manifest = [{'index':i,'image_name':p.name,'dataset_source':s,'image_path':str(p.resolve()),
                     'source_sha256':originals.get('images/'+p.name,''),'seed':seed,
                     'dataset_review_note':notes.get(p.name,'')} for i,(p,s) in enumerate(selected,1)]
        write_csv(output/'manifest.csv',manifest,list(manifest[0]))
        atomic_json(output/'input_hashes.json',originals)
    # Only construct the parser if an image actually needs inference.
    parser, init_ms, inference_count = None, 0., 0
    init_attempted, init_error = False, None
    rows, failures, flags_by_image, skipped = [], [], {}, 0
    for index, (path, source) in enumerate(selected, 1):
        start = time.perf_counter()
        row = {'image_name':path.name,'dataset_source':source,'status':'success','warning':'','reason':''}
        try:
            receipt = load_receipt(output,path.name,originals.get('images/'+path.name,'')) if resume else None
            if receipt:
                row = receipt['row']
                flags_by_image[path.name] = receipt['flags']
                skipped += 1
                LOG.info('[%d/%d] %s verified; skipped',index,len(selected),path.name)
                rows.append(row)
                continue
            if not path.is_file(): raise FileNotFoundError('image_missing')
            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if image is None: raise ValueError('image_unreadable')
            if image.shape != (256,256,3) or image.dtype != np.uint8:
                raise ValueError(f'expected_uint8_BGR_256x256: {image.shape}, {image.dtype}')
            if parser is None:
                init_start = time.perf_counter()
                if init_attempted:
                    raise RuntimeError(f'Model startup already failed: {init_error}')
                init_attempted = True
                try:
                    loaded_parser, loaded_model = parser_factory()
                    if resume and loaded_model != model_info:
                        raise ValueError('Model/environment differs from initial run')
                except Exception as error:
                    init_error = str(error)
                    raise
                parser = loaded_parser
                init_ms = (time.perf_counter()-init_start)*1000
                model_info = loaded_model
                config = {'dataset':str(dataset),'script_sha256':code_hash,'thresholds':THRESHOLDS,
                          'split_sources':split_sources,'seed':seed,'model':model_info,'metadata_hashes':metadata_hashes,
                          'skin_label':1,'hair_label':17,'erosion':{'kernel':[3,3],'iterations':1},
                          'multi_person_method':'not_run; dataset review notes are unverified historical hints',
                          'python':sys.version,'opencv':cv2.__version__}
                if not resume: atomic_json(output/'run_config.json',config)
                start += (time.perf_counter()-init_start)  # Exclude model startup from per-image timing.
            before = image.copy()
            inference_count += 1
            masks = make_masks(parser.parse(image))
            if not np.array_equal(image,before): raise ValueError('parser_modified_input_array')
            numbers, flags = quality(masks)
            row.update(numbers)
            note = notes.get(path.name,'')
            row['dataset_review_note'] = note
            row['face_count_check'] = 'not_run'
            if note:
                row['warning'] = ';'.join(filter(None,[row['warning'],'dataset_review_note:'+note]))
            artifact_data = {}
            for region, mask_path in output_masks(output,path.name).items():
                ok, encoded = cv2.imencode('.png',masks[region])
                if not ok: raise OSError('Mask encoding failed')
                artifact_data[mask_path] = encoded.tobytes()
            ok, encoded = cv2.imencode('.png',preview(image,masks))
            if not ok: raise OSError('Preview encoding failed')
            artifact_data[output/'previews'/f'{path.stem}_preview.png'] = encoded.tobytes()
            # All inference/encoding completes before any mask is written. Existing
            # identical partial files are retained; conflicting files are never replaced.
            for target,data in artifact_data.items():
                if target.exists() and target.read_bytes()!=data:
                    raise ValueError(f'Existing artifact differs; refused overwrite: {target.name}')
            for target,data in artifact_data.items(): write_once(target,data)
            row['processing_time_ms'] = round((time.perf_counter()-start)*1000,3)
            atomic_json(output/'receipts'/f'{path.stem}.json',{
                'source_sha256':originals.get('images/'+path.name,''),'row':row,'flags':flags,
                'artifacts':{p.relative_to(output).as_posix():hashlib.sha256(data).hexdigest() for p,data in artifact_data.items()},
                'validation':'format/hash checked; semantic quality not confirmed'})
            flags_by_image[path.name] = flags
        except Exception as error:
            row.update(status='failed',reason=f'{type(error).__name__}: {error}')
            row['warning'] = ';'.join(filter(None,[row['warning'],'processing_failed']))
            row['processing_time_ms'] = round((time.perf_counter()-start)*1000,3)
            failures.append({'image_name':path.name,'dataset_source':source,'reason':row['reason']})
        rows.append(row)
        LOG.info('[%d/%d] %s %s %s',index,len(selected),path.name,row['status'],row['warning'])
        write_csv(output/'metrics.csv',rows,FIELDS)
        write_csv(output/'failed_images.csv',failures,['image_name','dataset_source','reason'])
    # Final write also covers no-op resumes, preserving original per-image measurements.
    write_csv(output/'metrics.csv',rows,FIELDS)
    write_csv(output/'failed_images.csv',failures,['image_name','dataset_source','reason'])
    after = protected_hashes(dataset)
    changed = sorted(n for n in originals.keys()|after.keys() if originals.get(n)!=after.get(n))
    page_start = time.perf_counter()
    pages = save_contact_pages(rows,output,split_sources)
    page_ms = (time.perf_counter()-page_start)*1000
    validation = validate_outputs(selected,output,originals,rows)
    atomic_json(output/'validation.json',validation)
    summary = {'seed':seed,'selected':len(selected),'successful':sum(r['status']=='success' for r in rows),
               'failed':len(failures),'images_with_warnings':sum(bool(r['warning']) for r in rows),
               'heuristic_flagged_masks':sum(bool(v) for flags in flags_by_image.values() for v in flags.values()),
               'flagged_masks_by_type':{r:sum(bool(f[r]) for f in flags_by_image.values()) for r in ('skin','hair','skin_clean','hair_clean')},
               'warning_counts':dict(Counter(w for r in rows for w in r['warning'].split(';') if w)),
               'thresholds':THRESHOLDS,'model':locals().get('model_info',{}),'initialization_time_ms':init_ms,
               'opencv':cv2.__version__,'protected_input_files':len(originals),'changed_original_files':changed,
               'input_audit_sha256':hashlib.sha256(json.dumps(originals,sort_keys=True).encode()).hexdigest(),
               'by_source':{},'validation':validation,'contact_pages':len(pages),'contact_sheet_time_ms':page_ms,
               'inference_images_this_attempt':inference_count,'verified_images_skipped':skipped,
               'attempt_wall_time_ms':(time.perf_counter()-started)*1000}
    for source in ('CFD','HF'):
        subset=[r for r in rows if r['dataset_source']==source]
        success=[r for r in subset if r['status']=='success']
        stats={'selected':len(subset),'successful':len(success),'failed':len(subset)-len(success),
               'warning_images':sum(bool(r['warning']) for r in subset)}
        for key in ('skin_pixels','hair_pixels','skin_clean_pixels','hair_clean_pixels','skin_area_ratio','hair_area_ratio',
                    'skin_clean_area_ratio','hair_clean_area_ratio','erosion_skin_loss_ratio','erosion_hair_loss_ratio','processing_time_ms'):
            values=[r[key] for r in success if r.get(key,'')!='']
            stats[key]={'mean':float(np.mean(values)),'median':float(np.median(values)),
                        'min':float(np.min(values)),'max':float(np.max(values))} if values else None
        summary['by_source'][source]=stats
    atomic_json(output/'summary.json',summary)
    atomic_json(attempt/'summary.json',summary)
    write_csv(output/'review_candidates.csv',[r for r in rows if r['warning']],FIELDS)
    atomic_json(output/'mask_warnings.json',flags_by_image)
    if changed: raise RuntimeError(f'Original inputs changed during execution: {changed}')
    if validation['errors']: raise RuntimeError('Output validation failed; inspect validation.json. Masks were not overwritten.')
    return summary


def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--dataset',type=Path,default=DATASET)
    cli.add_argument('--output',type=Path)
    cli.add_argument('--seed',type=int,default=42)
    cli.add_argument('--all',action='store_true',help='Process all CFD/HF PNG images instead of random 100')
    cli.add_argument('--retry-failed',action='store_true',help='Verify and skip completed images; retry missing/failed receipts without replacing masks')
    args=cli.parse_args(argv)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',stream=sys.stdout)
    output=args.output or (PROJECT_ROOT/'outputs/B_color/uniface_full' if args.all else DEFAULT_OUTPUT)
    try:
        allowed_root=(PROJECT_ROOT/'outputs/B_color').resolve()
        if output.resolve()==allowed_root or allowed_root not in output.resolve().parents:
            raise ValueError('CLI outputs must be in a dedicated subdirectory of outputs/B_color')
        if args.all and (output.resolve()==DEFAULT_OUTPUT.resolve() or DEFAULT_OUTPUT.resolve() in output.resolve().parents):
            raise ValueError('Full mode cannot use the protected batch-100 output directory')
        selected=select_all_images(args.dataset/'images') if args.all else select_images(args.dataset/'images',args.seed)
        result=run_batch(selected,args.dataset,output,seed=args.seed,resume=args.retry_failed,split_sources=args.all)
    except (OSError,ValueError,RuntimeError) as error:
        LOG.error('%s',error)
        return 1
    print(json.dumps({k:result[k] for k in ('selected','successful','failed','images_with_warnings','heuristic_flagged_masks')},indent=2))
    return 1 if result['failed'] else 0


if __name__=='__main__':
    raise SystemExit(main())
