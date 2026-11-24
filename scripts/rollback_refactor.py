"""Restore the pre-refactor snapshot without deleting new trees. Dry-run by default."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from shared.paths import PROJECT_ROOT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup',type=Path)
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    backup=args.backup or PROJECT_ROOT/'.refactor_backup'/(PROJECT_ROOT/'.refactor_backup/latest.txt').read_text().strip()
    allowed=json.loads((backup/'post_original_paths.json').read_text())
    operations=[]; conflicts=[]
    with zipfile.ZipFile(backup/'snapshot.zip') as archive:
        for entry in archive.infolist():
            dest=(PROJECT_ROOT/entry.filename).resolve()
            if not dest.is_relative_to(PROJECT_ROOT) or entry.is_dir():
                raise ValueError('Unsafe snapshot path')
            original=archive.read(entry)
            if dest.exists():
                current=sha(dest.read_bytes())
                if current==sha(original):continue
                if current!=allowed.get(entry.filename):
                    conflicts.append(entry.filename);continue
            operations.append((dest,original))
    if conflicts:
        raise SystemExit('Refusing to overwrite files changed since refactor: '+', '.join(conflicts))
    print(f'{len(operations)} original files to restore. New package/output trees are retained; nothing is deleted.')
    if args.restore:
        for dest,data in operations:
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        print('Original paths/content restored. Restart running Python tools before use.')
    else:print('Dry run only. Add --restore to execute.')


if __name__=='__main__':main()
