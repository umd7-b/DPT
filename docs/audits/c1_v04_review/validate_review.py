"""Read-only checks of review records, not identity verification or approval."""
from pathlib import Path
import argparse
import csv
import datetime
import json

import build_review as bundle

ALLOWED = {'ACCEPT', 'REJECT', 'UNCERTAIN', 'NOT_REVIEWED'}
ANSWERS = {'YES', 'NO', 'UNCERTAIN', 'NOT_ANSWERED'}
SIDES = {'VIEWER', 'IMAGE_SUBJECT', 'UNCERTAIN', 'NOT_ANSWERED'}


def file_path(base, value):
    path = Path(value)
    return path if path.is_absolute() else base / path


def evidence_hash(base, path, expected, label):
    value = file_path(base, path)
    if not path or not value.is_file() or not expected or bundle.source.digest(value) != expected:
        raise ValueError(label + ': missing file or SHA-256 mismatch')


def validate(rows, manifest, evidence_base=bundle.OUT, authorities=None):
    evidence_base = Path(evidence_base)
    authorities = {} if authorities is None else authorities
    images = {r['image_id']: r for r in manifest['images']}
    expected = {(key, region, version) for key in images for region in bundle.REGIONS for version in bundle.PINS}
    if len(rows) != len(expected): raise ValueError('Expected exactly800 image/ROI/contract rows; cannot drop difficult cases')
    seen, counts = set(), {s: 0 for s in sorted(ALLOWED)}
    for row in rows:
        if not set(bundle.FIELDS).issubset(row): raise ValueError('Missing required CSV columns')
        key = (row['image_id'], row['roi_name'], row['contract_version'])
        if key not in expected or key in seen: raise ValueError('Unknown or duplicate image/ROI/contract key')
        seen.add(key)
        image, region, version = images[key[0]], key[1], key[2]
        immutable = dict(contract_content_sha256=bundle.PINS[version], image_sha256=image['image_sha256'],
            geometry_status=image['measurements'][version][region]['geometry_status'], evidence_path=image['evidence_path'])
        for field, value in immutable.items():
            if row[field] != value: raise ValueError('Immutable evidence field changed: ' + field)
        if not file_path(evidence_base, row['evidence_path']).is_file(): raise ValueError('Review picture evidence missing')
        status = row['anatomy_review_status']
        if status not in ALLOWED: raise ValueError('Invalid anatomy_review_status')
        counts[status] += 1
        if any(row[q] not in ANSWERS for q in bundle.QUESTIONS): raise ValueError('Invalid question answer')
        if row['left_right_reference'] not in SIDES: raise ValueError('Invalid left/right reference')
        if status == 'NOT_REVIEWED': continue
        if not row['reviewer'].strip() or not row['review_date'].strip(): raise ValueError('Human reviewer and review_date required')
        try:
            parsed_date = datetime.date.fromisoformat(row['review_date'])
            if parsed_date.isoformat() != row['review_date']: raise ValueError('Non-extended ISO date')
        except ValueError: raise ValueError('review_date must be ISO YYYY-MM-DD') from None
        if any(row[q] == 'NOT_ANSWERED' for q in bundle.QUESTIONS) or row['left_right_reference'] == 'NOT_ANSWERED':
            raise ValueError('Human review must answer all six prompts, including UNCERTAIN when appropriate')
        if not row['occlusion_observation'].strip(): raise ValueError('Human occlusion observation required')
        if not row['reason'].strip() and not row['decision_notes'].strip(): raise ValueError('Human reason or decision_notes required')
        authority = authorities.get(row['reviewer'])
        if not authority or authority['authority_confirmation_status'] != 'CONFIRMED_BY_PROJECT_OWNER':
            raise ValueError('Reviewer lacks recorded project-owner authority confirmation')
        if not authority['role'].strip(): raise ValueError('Authority role required')
        if row['reviewer_authority_evidence'] != authority['appointment_evidence_path']:
            raise ValueError('Reviewer authority evidence differs from registry')
        evidence_hash(evidence_base, authority['appointment_evidence_path'], authority['appointment_evidence_sha256'], 'Authority evidence')
        if row['decision_evidence_path'] == row['evidence_path']:
            raise ValueError('A rendered polygon page is not human decision evidence')
        evidence_hash(evidence_base, row['decision_evidence_path'], row['decision_evidence_sha256'], 'Human decision evidence')
    if seen != expected: raise ValueError('Incomplete image/ROI/contract set')
    return dict(structural_status='PASS', row_count=len(rows), anatomy_status_counts=counts,
        human_review_rows=len(rows) - counts['NOT_REVIEWED'],
        candidate_activated=False, approval_decision_issued=False,
        validation_scope='Syntax, provenance references and file integrity only; human identity/delegation/content authenticity still need independent confirmation. No global anatomical approval inferred.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, default=bundle.OUT / 'review_annotations.csv')
    parser.add_argument('--authority-register', type=Path, default=bundle.OUT / 'reviewer_authorities.csv')
    parser.add_argument('--evidence-base', type=Path, default=bundle.OUT)
    args = parser.parse_args()
    rows = bundle.source.read_csv(args.annotations)
    registry = bundle.source.read_csv(args.authority_register)
    authorities = {}
    for row in registry:
        if not row['reviewer'].strip() or row['reviewer'] in authorities:
            raise ValueError('Empty or duplicate reviewer in authority register')
        authorities[row['reviewer']] = row
    result = validate(rows, bundle.source.read_json(bundle.OUT / 'review_manifest.json'), args.evidence_base, authorities)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
