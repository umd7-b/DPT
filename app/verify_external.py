"""Run all existing Python suites without changing prior verification artifacts."""
from contextlib import redirect_stderr,redirect_stdout
import json
from pathlib import Path
import time
import unittest
from app.external_config import QA_EVIDENCE

E=QA_EVIDENCE

def main():
    E.mkdir(parents=True,exist_ok=True)
    results=[]
    for folder in ('tests','database/tests','app/tests'):
        name=folder.replace('/','_');start=time.monotonic()
        with (E/(name+'_tests.log')).open('w',encoding='utf8') as log,redirect_stderr(log),redirect_stdout(log):
            suite=unittest.TestLoader().discover(folder,pattern='test_*.py')
            run=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        item=dict(suite=folder,tests=run.testsRun,failures=[(t.id(),s) for t,s in run.failures],errors=[(t.id(),s) for t,s in run.errors],
            skipped=[(t.id(),s) for t,s in run.skipped],seconds=time.monotonic()-start,success=run.wasSuccessful())
        results.append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
    (E/'regression_tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
    if not all(r['success'] for r in results):raise SystemExit(1)

if __name__=='__main__':main()
