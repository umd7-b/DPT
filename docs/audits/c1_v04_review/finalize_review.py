"""Seal the preparation evidence without issuing human review decisions."""
from pathlib import Path
from html.parser import HTMLParser
import io
import json
import re
import subprocess
import unittest
from urllib.parse import unquote, urlsplit

import build_review as bundle
import validate_review
from verify_bundle import ReviewContractTests


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value: self.links.append(value)


def local_exists(parent, target):
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not parts.path: return True
    return (parent / unquote(parts.path)).is_file() or (parent / unquote(parts.path)).is_dir()


def main():
    out = bundle.OUT
    if (out / 'created_files_manifest.json').exists(): raise FileExistsError('Completed review package; no overwrite')
    manifest = bundle.source.read_json(out / 'review_manifest.json')
    validation = validate_review.validate(bundle.source.read_csv(out / 'review_annotations.csv'), manifest)
    assert validation['human_review_rows'] == 0
    decisions = bundle.source.read_csv(out / 'decision_register.csv')
    assert len(decisions) == 8 and all(r['decision_status'] == 'PENDING_AUTHORITY_REVIEW' for r in decisions)
    assert all(not r['authority_person_or_confirmed_source'] and not r['authority_evidence_path'] and not r['decision_date'] for r in decisions)
    assert bundle.source.read_csv(out / 'reviewer_authorities.csv') == []
    bad, link_count = [], 0
    for page in out.rglob('*.html'):
        parser = Links(); parser.feed(page.read_text(encoding='utf-8'))
        for target in parser.links:
            link_count += 1
            if not local_exists(page.parent, target): bad.append((str(page), target))
    docs = [bundle.ROOT / 'docs/audits' / name for name in [
        'C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md', 'C1_V04_DECISION_REGISTER.md', 'C1_V04_APPROVAL_READINESS.md']]
    for path in docs:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            # final_scope is created below; all other local links must already resolve.
            if target.endswith('c1_v04_review/final_scope.json'): continue
            if not local_exists(path.parent, target): bad.append((str(path), target))
    assert not bad, bad
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReviewContractTests))
    print(log.getvalue(), end='', flush=True)
    with (out / 'final_tests.log').open('x', encoding='utf-8') as stream: stream.write(log.getvalue())
    assert tests.wasSuccessful() and tests.testsRun == 9
    baseline = bundle.check_baseline()
    primary = bundle.source.read_json(out / 'verification.json')
    assert primary['status'] == 'PASS' and primary['raw_mask_round_trips'] == primary['binary_difference_checks'] == 800
    bundle.source.write_json(out / 'final_scope.json', dict(schema_id='C1_V04_REVIEW_PREPARATION_FINAL_SCOPE_v1',
        preparation_status='REVIEW_PACKAGE_READY_HUMAN_REVIEW_PENDING', baseline_file_count=len(baseline),
        baseline_sha256=bundle.source.digest(out / 'baseline_before.json'), changed_existing_files=[],
        review_images=100, annotation_rows=800, anatomy_status_counts=validation['anatomy_status_counts'],
        human_reviews_recorded=0, reviewers_with_recorded_authority=0, pending_convention_decisions=8,
        final_tests_run=tests.testsRun, test_failures=len(tests.failures), test_errors=len(tests.errors),
        html_links_checked=link_count, broken_links=[], candidate_activated=False,
        approval_issued=False, C1C2_vectors_created=0, LBP_HOG_calls=0, rank_queries=0,
        original_trial100_vectors_recomputed=0, SQLite_writes=0,
        old_AB_PDF_dataset_SQLite_calibration_trial100_remediation_preserved=True))
    paths = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=bundle.ROOT, text=True).splitlines()
    files = []
    for name in sorted(paths):
        p = bundle.ROOT / name
        if p.is_file() and str(p.resolve()) not in baseline:
            files.append(dict(path=name, bytes=p.stat().st_size, sha256=bundle.source.digest(p)))
    bundle.source.write_json(out / 'created_files_manifest.json', dict(schema_id='C1_V04_REVIEW_CREATED_FILES_v1',
        self_excluded=True, preparation_status='REVIEW_PACKAGE_READY_HUMAN_REVIEW_PENDING', files=files))
    print('Prepared100 review images,800 NOT_REVIEWED rows,8 PENDING decisions;9 tests PASS;',
          len(baseline), 'old files unchanged;', len(files), 'new files manifested', flush=True)


if __name__ == '__main__': main()
