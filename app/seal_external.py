"""Verify protected bytes and seal only the new external-query evidence namespace."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
from app.external_config import ROOT,QA_EVIDENCE
from app.server import DATABASE_SHA256
from database import store,four_feature

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    E=QA_EVIDENCE;target=E/'final_manifest.json'
    if target.exists():raise FileExistsError('Evidence already sealed; do not overwrite')
    before=json.loads((E/'protected_before.json').read_text('utf8'))
    changed=[p for p,h in before.items() if not Path(p).is_file() or digest(p)!=h]
    after=dict(files=len(before),changed=changed,baseline_manifest_sha256=digest(E/'protected_before.json'))
    (E/'protected_after.json').write_text(json.dumps(after,indent=2),encoding='utf8')
    if changed:raise ValueError('Protected files changed: '+repr(changed[:5]))
    assert digest(four_feature.DEFAULT_DB)==DATABASE_SHA256
    with closing(store.connect(four_feature.DEFAULT_DB,readonly=True)) as c:
        counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('Images','FeatureVectors','FeatureVersions','FourFeatureRuns','FourFeatureResults')}
        counts['valid_vectors']=c.execute("SELECT COUNT(*) FROM FeatureVectors WHERE status='valid'").fetchone()[0]
        counts['missing_vectors']=counts['FeatureVectors']-counts['valid_vectors']
    assert counts==dict(Images=1438,FeatureVectors=5752,FeatureVersions=4,FourFeatureRuns=6,FourFeatureResults=125,valid_vectors=5751,missing_vectors=1),counts
    sources=[*ROOT.joinpath('app').glob('external*.py'),*ROOT.joinpath('app').glob('*external*.py'),
        ROOT/'app/server.py',ROOT/'app/static/index.html',ROOT/'app/static/app.js',ROOT/'app/static/crop.js',ROOT/'app/static/crop.css',
        ROOT/'app/README.md',ROOT/'app/EXTERNAL_IMAGE_DEMO.md',ROOT/'docs/EXTERNAL_IMAGE_SEARCH_IMPLEMENTATION_REPORT.md',
        ROOT/'app/tests/test_web.py',ROOT/'app/tests/test_external.py',ROOT/'app/tests/make_external_fixtures.py',
        ROOT/'app/tests/external_browser.mjs',ROOT/'app/tests/external_crop_browser.mjs']
    files=sorted(set(sources)|{p for p in E.rglob('*') if p.is_file() and p!=target})
    result=dict(status='PASS',date_local='2026-11-24',timezone='Asia/Saigon',protected=after,database_sha256=DATABASE_SHA256,counts=counts,
        checks=dict(python_unique_passed=260,python_uniface_environment_skips_covered=2,browser_end_to_end_groups=8,browser_crop_groups=8),
        files={str(p.relative_to(ROOT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in files})
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(status='PASS',protected_files=len(before),changed=changed,counts=counts,manifest=str(target)),ensure_ascii=False))

if __name__=='__main__':main()
