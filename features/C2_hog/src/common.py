"""Small standard-library I/O; no feature/environment cross-imports."""
from pathlib import Path
from contextlib import closing
import csv
import json
import sqlite3

from . import root_hog as hog

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'outputs/C2_hog'
TRIAL_PLAN=ROOT/'outputs/C1_lbp/trial100_spec_v0_1/input_trial100_manifest.json'


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False,
                  default=lambda obj:obj.tolist() if hasattr(obj,'tolist') else obj.item())
        stream.write('\n')


def save_csv(path,rows,fields=None):
    with Path(path).open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields or list(rows[0]));writer.writeheader();writer.writerows(rows)


def baseline_check():
    baseline=read_json(BASE/'evidence/baseline_before.json')
    changed=[p for p,h in baseline.items() if not Path(p).is_file() or hog.sha256(p)!=h]
    if changed:raise ValueError('Frozen artifacts changed: '+repr(changed[:5]))
    frozen=read_json(BASE/'evidence/spec_lock_before_tests.json'); current=hog.lock()
    if (current['spec_hash']!=frozen['spec_content_sha256'] or current['spec_file_sha256']!=frozen['spec_file_sha256']
            or current['implementation_sha256']!=frozen['kernel_sha256']):raise ValueError('C2 conventions/source changed after freeze')
    return baseline


def catalog():
    db=ROOT/'database/data/portrait_ab_v2.sqlite3'
    with closing(sqlite3.connect(db.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as con:
        con.row_factory=sqlite3.Row;rows=[dict(row) for row in con.execute('SELECT * FROM Images')]
    if len(rows)!=1438 or len({r['image_id'] for r in rows})!=1438:raise ValueError('Unexpected catalog identities')
    return {r['image_id']:r for r in rows}


def identities(rows):
    """Metadata row permutation never defines feature ordering or identity."""
    mapping={r['image_id']:r for r in rows}
    if len(mapping)!=len(rows):raise ValueError('Duplicate image_id')
    return sorted(mapping)
