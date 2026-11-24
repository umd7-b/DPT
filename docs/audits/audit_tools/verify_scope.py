"""Final hash/scope/report consistency verification; audit output only."""
from common import *
from collections import Counter

before=json.loads((EVIDENCE/'protected_before.json').read_text(encoding='utf-8'))
supplement=json.loads((EVIDENCE/'protected_supplement_legacy_previews.json').read_text(encoding='utf-8'))
protected=dict(before,**supplement)
changed=[];missing=[]
for name,expected in protected.items():
    path=Path(name)
    if not path.is_file():missing.append(name)
    elif sha(path)!=expected:changed.append(name)
assert not changed and not missing,dict(changed=changed,missing=missing)
roots=['features','src','shared','retrieval','tests','scripts','models','annotations','outputs/A_geometry',
       'outputs/B_color','outputs/retrieval/ab_experiment','outputs/retrieval/ab_validation','outputs/retrieval/search_results']
new_protected=[]
for folder in [ROOT/name for name in roots]+[DATA]:
    for p in folder.rglob('*'):
        if p.is_file() and not any(part.startswith('.venv') or part=='__pycache__' for part in p.parts):
            if str(p.resolve()) not in protected:new_protected.append(str(p))
assert not new_protected,new_protected
reports=['FINAL_AB_COMPLIANCE_AUDIT.md','A150_FORMULA_VERIFICATION.md','B144_FORMULA_VERIFICATION.md',
         'DATASET_REPORT_COMPLIANCE.md','AB_RETRIEVAL_COMPLIANCE.md','REMEDIATION_PLAN.md']
for name in reports:
    text=(ROOT/'docs/audits'/name).read_text(encoding='utf-8')
    assert '| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |' in text
register=json.loads((EVIDENCE/'requirements_register.json').read_text(encoding='utf-8'))
counts=json.loads((EVIDENCE/'status_counts.json').read_text(encoding='utf-8'))
assert counts['total']==len(register)==len({r['id'] for r in register})
assert dict(Counter(r['status'] for r in register))==counts['counts']
for name,count in [('unit_tests_a.log',23),('unit_tests_b_ab.log',16),('existing_tests_ab.log',17),('existing_tests_color.log',40)]:
    log=(EVIDENCE/name).read_text(encoding='utf-8')
    assert f'Ran {count} tests' in log and log.rstrip().endswith('OK'),name
assert hashlib.sha256(Path('C:/Users/USER/Downloads/csdldpt.pdf').read_bytes()).hexdigest()=='8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80'
scope=dict(status='PASS',initial_snapshot_files=len(before),supplemental_legacy_preview_files=len(supplement),
    protected_files_checked=len(protected),changed_files=changed,missing_files=missing,
    new_files_in_protected_roots=new_protected,report_files=reports,requirements=len(register),status_counts=counts['counts'],
    independent_tests_passed=39,existing_tests_passed=57,official_vectors_replaced=0,
    pdf_unchanged=True,c1_c2_unchanged=True,dataset_unchanged=True,
    snapshot_limitations='Environments/__pycache__ excluded; three legacy A-only previews supplemented after initial read, before audit rendering; source packages read outside snapshot are not claimed as hashed inputs.')
dump('scope_validation.json',scope)
files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
       for p in sorted((ROOT/'docs/audits').rglob('*')) if p.is_file() and p.name!='created_files_manifest.json' and '__pycache__' not in p.parts]
dump('created_files_manifest.json',dict(files=files,count=len(files),note='Only new docs/audits files; manifest excludes itself. Earlier A+B working-tree changes predate this audit.'))
print(json.dumps(scope,indent=2))
