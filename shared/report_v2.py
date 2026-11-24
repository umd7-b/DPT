"""I/O and provenance contracts for report v2; no legacy entry point changes."""
from pathlib import Path
import csv
import hashlib
import json

import numpy as np
from shared.paths import PROJECT_ROOT

REPORT = Path('C:/Users/USER/Downloads/csdldpt.pdf')
REPORT_SHA256 = '8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        if not rows:
            raise ValueError('Empty CSV needs explicit fields')
        fields = list(rows[0])
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fresh_output(path, namespace, prefix):
    """Never reuse a gallery directory, including an incomplete prior build."""
    path, namespace = Path(path).resolve(), Path(namespace).resolve()
    if path.parent != namespace or not path.name.startswith(prefix):
        raise ValueError(f'Use a new {namespace / (prefix + "*")} directory')
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite an existing artifact directory: {path}')
    path.mkdir(parents=True)
    return path


def provenance(paths):
    if digest(REPORT) != REPORT_SHA256:
        raise ValueError('Official PDF hash mismatch')
    return {str(Path(p).resolve()): digest(p) for p in [REPORT, *paths]}


def verify_sources(fingerprints):
    for name, expected in fingerprints.items():
        if digest(name) != expected:
            raise ValueError('Source changed: ' + name)


def save_integrity(directory, names):
    directory = Path(directory)
    write_json(directory / 'gallery_integrity.json', {name: digest(directory / name) for name in names})


def verify_integrity(directory):
    directory = Path(directory).resolve()
    values = read_json(directory / 'gallery_integrity.json')
    for name, expected in values.items():
        path = (directory / name).resolve()
        if directory not in path.parents or digest(path) != expected:
            raise ValueError('V2 artifact integrity mismatch: ' + name)
    return values


def finite_features(value, dimension, min_rows=None):
    array = np.asarray(value, dtype=np.float64)
    if array.ndim not in (1, 2) or array.shape[-1] != dimension or not np.isfinite(array).all():
        raise ValueError(f'Expected finite {dimension}-dimensional features')
    if min_rows is not None and (array.ndim != 2 or len(array) < min_rows):
        raise ValueError(f'Expected at least {min_rows} gallery rows')
    return array


def save_stats(path, stats):
    np.savez(path, **stats)


def load_stats(path):
    with np.load(path, allow_pickle=False) as file:
        return {key: file[key].copy() for key in file.files}


def pair_ids_digest(pairs):
    payload = json.dumps(list(pairs), ensure_ascii=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()
