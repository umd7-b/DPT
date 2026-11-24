"""Read-only application-storage/provenance inventory; never open/create a DB."""
from pathlib import Path
import ast
from collections import Counter
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_csv, write_json, save_csv

E = ROOT / 'docs/audits/pre_c_evidence'
DATA = Path('D:/TuNam4/dataset_HF_CFD_final')
WANTED = ['hf_merged_00333', 'hf_merged_00561', 'hf_merged_00722', 'hf_merged_00209', 'hf_merged_00694']


def excluded(path):
    return any(part.startswith(('.venv', 'chrome_profile')) or part in ('.git', '__pycache__', '.refactor_backup') for part in path.parts)


def main():
    catalog = read_csv(DATA / 'metadata.csv')
    source_rows = read_csv(DATA / 'hf_provenance.csv')
    b_rows = read_csv(ROOT / 'outputs/B_color/color_features_report_v2/manifest.csv')
    ds_index = {r['image_id']: r for r in catalog}
    b_index = {r['image_id']: r for r in b_rows}
    provenance_index = {}
    for row in source_rows:
        provenance_index.setdefault(Path(row['filename']).stem, []).append(row)
    search_roots = [DATA, ROOT]
    for name in ['dataset_hf_merged_v1', 'dataset_v1_1482', 'dataset_v2', 'support_for_tasks_2_3_4_5']:
        for parent in [DATA.parent, Path('D:/datasetCSDL'), Path('C:/Users/USER/Downloads')]:
            path = parent / name
            if path.is_dir():
                search_roots.append(path)
    basename_index = {}
    for root in search_roots:
        for path in root.rglob('*'):
            if path.is_file() and not excluded(path) and E not in path.parents:
                basename_index.setdefault(path.name, []).append(str(path.resolve()))
    checks = []
    for key in WANTED:
        row = ds_index[key]
        assert digest(DATA / 'images' / row['filename']) == row['sha256']
        originals = json.loads(row['original_path']) if row['original_path'].startswith('[') else [row['original_path']]
        tokens = list(originals)
        tokens += [r['source_filename'] for r in provenance_index.get(key, [])]
        tokens += [r['original_path'] for r in provenance_index.get(key, [])]
        parquet = []
        for token in tokens:
            match = re.match(r'(.+\.parquet)_row_(\d+)$', token)
            if match:
                parquet.append(dict(filename=match[1], row=int(match[2])))
        candidate_names = sorted(set(Path(t).name for t in tokens) | {p['filename'] for p in parquet})
        hits = {name: basename_index.get(name, []) for name in candidate_names}
        checks.append(dict(image_id=key, image_name=row['filename'], source_sha256=row['sha256'],
            source_dataset=row['source_dataset'], original_tokens=originals,
            provenance_records=provenance_index.get(key, []), parquet_row_tokens=parquet,
            source_person_id=row['source_person_id'], candidates_checked=hits,
            replacement_image_verified=False,
            replacement_limit='No validated alternate source image/identity found in the named local search scope; external source availability unknown',
            b_status=b_index[key]['status'], b_reason=b_index[key]['reason'],
            b_hair_pixels=int(b_index[key]['hair_pixels']), b_skin_pixels=int(b_index[key]['skin_pixels'])))
    write_json(E / 'dataset_source_review.json', dict(search_roots=[str(p) for p in search_roots],
        records=checks, source_metadata_sha256=digest(DATA / 'metadata.csv'), hf_provenance_sha256=digest(DATA / 'hf_provenance.csv'),
        note='No inferred person IDs/demographics; parquet_stream token lacks repository/revision/shard locator; no source image altered'))

    drivers = {'sqlite3', 'sqlalchemy', 'psycopg', 'psycopg2', 'pymysql', 'mysql', 'pymongo', 'duckdb',
               'peewee', 'tortoise', 'asyncpg', 'pyodbc', 'databases'}
    sql_pattern = re.compile(r'\b(CREATE\s+TABLE|INSERT\s+INTO|SELECT\s+.+?\s+FROM|sqlite3\.connect|create_engine|MongoClient|DATABASE_URL)\b', re.I)
    scan = []
    for folder in ['features', 'src', 'shared', 'retrieval', 'scripts', 'tests']:
        for path in sorted((ROOT / folder).rglob('*.py')):
            if excluded(path):
                continue
            text = path.read_text(encoding='utf-8-sig')
            tree = ast.parse(text)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports += [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            scan.append(dict(path=str(path.relative_to(ROOT)), sha256=digest(path),
                database_imports=[n for n in imports if n.split('.')[0] in drivers],
                database_pattern_lines=[i for i, line in enumerate(text.splitlines(), 1) if sql_pattern.search(line)],
                functions=[dict(name=n.name, line=n.lineno) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]))
    db_files = []
    config_paths = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or excluded(path) or E in path.parents:
            continue
        if path.suffix.lower() in ('.db', '.sqlite', '.sqlite3', '.sql'):
            db_files.append(str(path.relative_to(ROOT)))
        if path.name.lower().startswith(('docker-compose', 'alembic')) or path.name in ('pyproject.toml', 'requirements.txt'):
            config_paths.append(str(path.relative_to(ROOT)))
    a_metadata = read_csv(ROOT / 'outputs/A_geometry/features_report_v2/metadata.csv')
    actual_storage = [
        dict(role='image catalog', file='D:/TuNam4/dataset_HF_CFD_final/metadata.csv', format='CSV', fields=list(catalog[0])),
        dict(role='A feature identity/row map', file='outputs/A_geometry/features_report_v2/metadata.csv', format='CSV', fields=list(a_metadata[0])),
        dict(role='B full identity/status map', file='outputs/B_color/color_features_report_v2/manifest.csv', format='CSV', fields=list(b_rows[0])),
        dict(role='vectors A/B', file='outputs/{A_geometry/features_report_v2,B_color/color_features_report_v2}/*.npy', format='NumPy arrays', fields=[]),
        dict(role='normalization statistics', file='outputs/{A_geometry/features_report_v2,B_color/color_features_report_v2}/*.npz', format='NumPy ZIP archives', fields=[]),
        dict(role='retrieval/calibration', file='outputs/retrieval/ab_report_v2/{queries,calibration}', format='CSV/JSON/PNG', fields=[])]
    write_json(E / 'database_inventory.json', dict(active_python_files=len(scan), source_scan=scan,
        db_driver_import_count=sum(len(r['database_imports']) for r in scan),
        db_pattern_match_count=sum(len(r['database_pattern_lines']) for r in scan), database_or_sql_files=db_files,
        deployment_config_candidates=config_paths, installed_db_service_probe_performed=False,
        live_database_connection_attempted=False, database_created=False, actual_storage=actual_storage,
        person_ids_present=sum(bool(r['source_person_id']) for r in catalog),
        person_ids_missing=sum(not r['source_person_id'] for r in catalog),
        source_scoped_person_ids=len({(r['source'], r['source_person_id']) for r in catalog if r['source_person_id']}),
        eye_xy_columns_in_catalog=[k for k in catalog[0] if re.search(r'eye.*[xy]|[xy].*eye', k, re.I)],
        eye_xy_columns_in_a_metadata=[k for k in a_metadata[0] if re.search(r'eye.*[xy]|[xy].*eye', k, re.I)],
        scope='Active project source + non-environment/non-browser files; audit reports/snapshots are not application DB implementation; no claim about an unknown external DB'))
    print(json.dumps(dict(dataset_cases=len(checks), validated_replacement_images=0, active_python_files=len(scan),
        db_driver_imports=sum(len(r['database_imports']) for r in scan), db_pattern_matches=sum(len(r['database_pattern_lines']) for r in scan),
        database_or_sql_files=db_files), indent=2))


if __name__ == '__main__':
    main()
