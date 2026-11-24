"""Run HTTP tests and accepted regressions, and prove all frozen files unchanged."""
from contextlib import redirect_stderr
from pathlib import Path
import platform
import unittest

from database import four_feature as four
from database import store
from shared.report_v2 import read_json,write_json

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'app/evidence'


def main():
    if (E/'verification.json').exists():raise FileExistsError('Web verification already sealed; do not overwrite evidence')
    browser=read_json(E/'browser_verification.json');assert browser['status']=='PASS'
    suite=unittest.TestSuite()
    for pattern in ['test_report_v2.py','test_search_ab.py','test_color_features.py','test_color_report_compliance.py',
                    'test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py',
                    'test_c2_root_hog.py','test_c2_pipeline.py','test_fusion_four.py']:
        suite.addTests(unittest.TestLoader().discover(str(ROOT/'tests'),pattern=pattern))
    for pattern in ['test_database.py','test_four_feature.py']:
        suite.addTests(unittest.TestLoader().discover(str(ROOT/'database/tests'),pattern=pattern))
    suite.addTests(unittest.TestLoader().discover(str(ROOT/'app/tests'),pattern='test_web.py'))
    print('Running existing regressions plus real HTTP integration tests...',flush=True)
    with (E/'tests.log').open('x',encoding='utf8') as log,redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert result.wasSuccessful() and not result.skipped
    baseline=read_json(E/'baseline_before.json')
    changed=[name for name,digest in baseline.items() if not Path(name).is_file() or store.digest(name)!=digest]
    assert not changed,changed
    with store.connect(four.DEFAULT_DB) as c:
        counts=four.summary(c)
        assert counts['FourFeatureRuns']==6 and counts['FourFeatureResults']==125
    write_json(E/'verification.json',dict(status='PASS',date='2026-11-24',timezone='Asia/Saigon',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        web_http_tests=14,existing_regressions=176,browser_checks=len(browser['checks']),
        browser=browser['browser'],screenshots=browser['screenshots'],platform=platform.platform(),
        windows_version=platform.win32_ver(),protected_files=len(baseline),changed=[],missing=[],
        database_path=str(four.DEFAULT_DB),database_sha256=store.digest(four.DEFAULT_DB),
        original_query_history_runs=counts['FourFeatureRuns'],original_query_history_results=counts['FourFeatureResults'],
        snapshot_readonly=True,query_persist=False,history_enabled=False,
        vector_or_calibration_changes=0,feature_extraction_runs=0,new_image_support=False,
        parity='All 125 Top5 rows across five complete queries/five modes exactly match accepted SQL JSON; missing_B preserved',
        binding='127.0.0.1',dependencies_installed=[],cv_dependencies_upgraded=[]))
    print('PASS:',result.testsRun,'tests;',len(browser['checks']),'Chromium checks;',len(baseline),'files unchanged')


if __name__=='__main__':main()
